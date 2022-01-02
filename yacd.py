import base64
from io import BytesIO
import fsspec

from flask import Flask
from matplotlib.figure import Figure

import numpy as np
import pandas as pd
import plottingtools as pt

pt.darkmode()

from cachetools import cached, TTLCache

app = Flask(__name__)


def get_strain_data(
    url:
    str = "https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Daten/VOC_VOI_Tabelle.xlsx?__blob=publicationFile"
):
    STRAIN_MAPPING = {
        "B.1.1.7": "Alpha",
        "B.1.351": "Beta",
        "AY.1": "Delta",
        "P.1": "Gamma",
        "B.1.1.529": "Omicron",
    }

    # Grab data
    with fsspec.open(url) as fp:
        data = pd.read_excel(fp, sheet_name="VOC")

    # Only keep single calendar week entries. Use as index
    data = data[data.KW.str.len() == 4]
    data.set_index(data.KW.str[-2:].astype(int), inplace=True)

    # Only keep columns with strain fractions
    data = data.drop(columns=[
        c for c in data.columns if "Anteil" not in c or "Gesamt" in c
    ])

    # Change colnames to Greek names
    data.columns = data.columns.to_series().str.split("+").str[0].map(
        STRAIN_MAPPING.get)

    return data


def get_vaccination_data(
    url:
    str = "https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv"
) -> pd.DataFrame:
    # Read CSV table from web
    data = pd.read_table(url)

    # Convert date column to datetime data type for better plotting later
    data['date'] = pd.to_datetime(data['date'])

    # Calculate daily vaccinations, and their rolling means
    data["erst_daily"] = data.dosen_erst_kumulativ.diff(1)
    data["zweit_daily"] = data.dosen_zweit_kumulativ.diff(1)
    data["dritt_daily"] = data.dosen_dritt_kumulativ.diff(1)
    data["erst_rollingmean"] = data.rolling(window=7)["erst_daily"].mean()
    data["zweit_rollingmean"] = data.rolling(window=7)["zweit_daily"].mean()
    data["dritt_rollingmean"] = data.rolling(window=7)["dritt_daily"].mean()

    return data


def get_case_data(
    url:
    str = "https://raw.githubusercontent.com/robert-koch-institut/SARS-CoV-2-Nowcasting_und_-R-Schaetzung/main/Nowcast_R_aktuell.csv"
) -> pd.DataFrame:
    # Read CSV table from web
    data = pd.read_table(url, sep=",")

    # Convert date column to datetime data type for better plotting later
    data['Datum'] = pd.to_datetime(data['Datum'])

    # Rolling mean
    data["cases_rollingmean"] = data.rolling(
        window=7)["PS_COVID_Faelle"].mean()

    return data


def get_bed_data(url: str = "") -> pd.DataFrame:
    # Read CSV table from web
    data=pd.read_table('https://diviexchange.blob.core.windows.net/%24web/zeitreihe-tagesdaten.csv',\
                  sep=",")

    # Convert date column to datetime data type for better plotting later
    data['date'] = pd.to_datetime(data['date'])

    # Aggregate per day
    data = data.drop(columns=[
        'bundesland', 'gemeindeschluessel', 'anzahl_standorte',
        'anzahl_meldebereiche'
    ])
    data = data.groupby("date").sum()
    data['date'] = data.index

    # Calculate sum of beds too
    data["betten_sum"] = data["betten_frei"] + data["betten_belegt"]

    return data


def get_all_data():
    return get_case_data(), get_strain_data(), get_vaccination_data(
    ), get_bed_data()


def make_vac_plot_cumul(data: pd.DataFrame) -> str:
    # Generate the figure **without using pyplot**.
    fig = Figure()
    ax = fig.subplots()

    # Plot
    pt.majorline(ax, data.date, data.dosen_erst_kumulativ, label="First")
    pt.majorline(ax, data.date, data.dosen_zweit_kumulativ, label="Second")
    pt.majorline(ax, data.date, data.dosen_dritt_kumulativ, label="Third")

    # Aesthetics
    fig.autofmt_xdate(bottom=0.2, rotation=40, ha='right')
    pt.despine(ax)
    pt.ticklabelsize(ax)
    pt.legend(ax)
    pt.labels(ax, "Date", "Cumul. Vaccinations")
    pt.limits(ax, None, (0, 1e8))
    fig.set_figheight(10)
    fig.set_figwidth(15)

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")

    # Convert to ASCII Base64
    return base64.b64encode(buf.getbuffer()).decode("ascii")


def make_vac_plot_daily(data: pd.DataFrame) -> str:
    # Generate the figure **without using pyplot**.
    fig = Figure()
    ax = fig.subplots()

    # Plot
    pt.polyscatter(ax, data.date, data.erst_daily)
    pt.polyscatter(ax, data.date, data.zweit_daily)
    pt.polyscatter(ax, data.date, data.dritt_daily)

    pt.majorline(ax, data.date, data.erst_rollingmean, label="First")
    pt.majorline(ax, data.date, data.zweit_rollingmean, label="Second")
    pt.majorline(ax, data.date, data.dritt_rollingmean, label="Third")

    # Aesthetics
    fig.autofmt_xdate(bottom=0.2, rotation=40, ha='right')
    pt.despine(ax)
    pt.ticklabelsize(ax)
    pt.legend(ax)
    pt.labels(ax, "Date", "Daily Vaccinations")
    ymax = np.max([
        np.max(data.erst_daily),
        np.max(data.zweit_daily),
        np.max(data.dritt_daily)
    ])
    ymax = round(ymax, -6) + 1000000
    pt.limits(ax, None, (0, ymax))
    fig.set_figheight(10)
    fig.set_figwidth(15)

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")

    # Convert to ASCII Base64
    return base64.b64encode(buf.getbuffer()).decode("ascii")


def make_case_plot(data: pd.DataFrame) -> str:
    # Generate the figure **without using pyplot**.
    fig = Figure()
    ax = fig.subplots()

    # Plot
    pt.polyscatter(ax, data.Datum, data.PS_COVID_Faelle)
    pt.majorline(ax, data.Datum, data.cases_rollingmean)

    # Aesthetics
    fig.autofmt_xdate(bottom=0.2, rotation=40, ha='right')
    pt.despine(ax)
    pt.ticklabelsize(ax)
    pt.labels(ax, "Date", "Daily Cases")
    ymax = round(max(data.PS_COVID_Faelle), -4) + 10000
    pt.limits(ax, None, (0, ymax))
    fig.set_figheight(10)
    fig.set_figwidth(15)

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")

    # Convert to ASCII Base64
    return base64.b64encode(buf.getbuffer()).decode("ascii")


def make_bed_plot(data: pd.DataFrame) -> str:
    # Generate the figure **without using pyplot**.
    fig = Figure()
    ax = fig.subplots()

    # Plot
    pt.majorline(ax, data.date, data.betten_frei, label="Free")
    pt.majorline(ax, data.date, data.betten_belegt, label="Occupied")
    pt.majorline(ax, data.date, data.betten_sum, label="Sum")

    # Aesthetics
    fig.autofmt_xdate(bottom=0.2, rotation=40, ha='right')
    pt.despine(ax)
    pt.ticklabelsize(ax)
    pt.labels(ax, "Date", "Beds")
    ymax = round(
        np.max([
            np.max(data.betten_frei),
            np.max(data.betten_belegt),
            np.max(data.betten_sum)
        ]), -4) + 10000
    pt.limits(ax, None, (0, ymax))
    pt.legend(ax)
    fig.set_figheight(10)
    fig.set_figwidth(15)

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")

    # Convert to ASCII Base64
    return base64.b64encode(buf.getbuffer()).decode("ascii")


def make_strain_plot(data: pd.DataFrame) -> str:
    # Generate the figure **without using pyplot**.
    fig = Figure()
    ax = fig.subplots()

    # Plot
    for c in data.columns:
        pt.majorline(ax, data.index, data[c], label=c)

    # Aesthetics
    fig.autofmt_xdate(bottom=0.2, rotation=40, ha='right')
    pt.despine(ax)
    pt.ticklabelsize(ax)
    pt.legend(ax)
    pt.labels(ax, "Calendar Week", "Fraction")
    pt.limits(ax, None, (0, 100.3))
    fig.set_figheight(10)
    fig.set_figwidth(15)

    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")

    # Convert to ASCII Base64
    return base64.b64encode(buf.getbuffer()).decode("ascii")


@cached(cache=TTLCache(maxsize=1, ttl=30 * 60))
def assemble_dashboard() -> str:
    case_data, strain_data, vac_data, bed_data = get_all_data()

    case_plot = make_case_plot(case_data)
    strain_plot = make_strain_plot(strain_data)
    vacplot_cumul = make_vac_plot_cumul(vac_data)
    vacplot_daily = make_vac_plot_daily(vac_data)
    bed_plot = make_bed_plot(bed_data)

    return f'''<html><head><link rel="stylesheet" href="/static/style.css"></head><body>
    <h1>Yet another Covid Dashboard!</h1>
    <h2>Cases (data polled from RKI github and RKI website)</h2>
    <img width=500px, src='data:image/png;base64,{case_plot}'/>
    <img width=500px, src='data:image/png;base64,{strain_plot}'/>
    <h2>Vaccinations (data polled from Impfdashboard)</h2>
    <img width=500px, src='data:image/png;base64,{vacplot_daily}'/>
    <img width=500px, src='data:image/png;base64,{vacplot_cumul}'/>
    <h2>Intensive Care Beds (data polled from DIVI website)</h2>
    <img width=500px, src='data:image/png;base64,{bed_plot}'/>
    </body></html>
    '''


@app.route("/")
def main():
    dashboard = assemble_dashboard()
    return dashboard
