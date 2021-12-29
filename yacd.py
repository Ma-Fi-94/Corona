import base64
from io import BytesIO

from flask import Flask
from matplotlib.figure import Figure

import numpy as np
import pandas as pd
import pt as pt
pt.darkmode()

import shutil
import requests

app = Flask(__name__)

def get_strain_data():
    # Grab data. Using a stream because direct download with pandas yields 403 Forbidden
    url = "https://www.rki.de/DE/Content/InfAZ/N/Neuartiges_Coronavirus/Daten/VOC_VOI_Tabelle.xlsx?__blob=publicationFile"
    response = requests.get(url, stream=True)
    with open('data.xlsx', 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

    # Read into pandas
    data = pd.read_excel("data.xlsx", sheet_name="VOC")

    # Only keep single calendar week entries. Use as index
    data = data[[len(x) == 4 for x in data.KW]]
    data.KW = [int(x[2:]) for x in data.KW]
    data.index = data.KW

    # Only keep columns with strain fractions
    data = data.loc[:, ["Anteil" in x for x in data.columns]]
    data = data.loc[:, [not "Gesamt" in x for x in data.columns]]

    # Change colnames to Greek names
    colnames = data.columns
    colnames_new = []
    for c in colnames:
        if "B.1.1.7" in c:
            colnames_new.append("Alpha")
        elif "B.1.351" in c:
            colnames_new.append("Beta")
        elif "AY.1" in c:
            colnames_new.append("Delta")
        elif "P.1" in c:
            colnames_new.append("Gamma")
        elif "B.1.1.529" in c:
            colnames_new.append("Omikron")
        else:
            colnames_new.append("Other")
    data.columns = colnames_new
    
    return data

def get_vaccination_data(url: str = "https://impfdashboard.de/static/data/germany_vaccinations_timeseries_v2.tsv") -> pd.DataFrame:
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

def get_case_data(url: str = "https://raw.githubusercontent.com/robert-koch-institut/SARS-CoV-2-Nowcasting_und_-R-Schaetzung/main/Nowcast_R_aktuell.csv") -> pd.DataFrame:
    # Read CSV table from web
    data = pd.read_table(url, sep=",")

    # Convert date column to datetime data type for better plotting later
    data['Datum'] = pd.to_datetime(data['Datum'])
    
    # Rolling mean
    data["cases_rollingmean"] = data.rolling(window=7)["PS_COVID_Faelle"].mean()


    return data

def get_bed_data(url: str = "") -> pd.DataFrame:
    # Read CSV table from web
    data=pd.read_table('https://diviexchange.blob.core.windows.net/%24web/zeitreihe-tagesdaten.csv',\
                  sep=",")
    
    # Convert date column to datetime data type for better plotting later
    data['date'] = pd.to_datetime(data['date'])
    
    # Aggregate per day
    data = data.drop(columns=['bundesland', 'gemeindeschluessel', 'anzahl_standorte',
        'anzahl_meldebereiche'])
    data = data.groupby("date").sum()
    data['date'] = data.index

    # Calculate sum of beds too
    data["betten_sum"] = data["betten_frei"] + data["betten_belegt"]

    return data

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
    pt.polyscatter(ax,data.date, data.erst_daily)
    pt.polyscatter(ax,data.date, data.zweit_daily)
    pt.polyscatter(ax,data.date, data.dritt_daily)

    pt.majorline(ax,data.date, data.erst_rollingmean, label="First")
    pt.majorline(ax,data.date, data.zweit_rollingmean, label="Second")
    pt.majorline(ax,data.date, data.dritt_rollingmean, label="Third")


    # Aesthetics
    fig.autofmt_xdate(bottom=0.2, rotation=40, ha='right')
    pt.despine(ax)
    pt.ticklabelsize(ax)
    pt.legend(ax)
    pt.labels(ax, "Date", "Daily Vaccinations")
    ymax = np.max([np.max(data.erst_daily), np.max(data.zweit_daily), np.max(data.dritt_daily)])
    ymax = round(ymax, -6)+1000000
    pt.limits(ax, None, (0,ymax))
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
    pt.legend(ax)
    pt.labels(ax, "Date", "Daily Cases")
    ymax = round(max(data.PS_COVID_Faelle), -4)+10000
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
    pt.legend(ax)
    pt.labels(ax, "Date", "Beds")
    ymax = round(np.max([np.max(data.betten_frei), np.max(data.betten_belegt), np.max(data.betten_sum)]), -4)+10000
    pt.limits(ax, None, (0, ymax))
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
    pt.limits(ax, None, (0, 100))
    fig.set_figheight(10)
    fig.set_figwidth(15)
    
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")

    # Convert to ASCII Base64
    return base64.b64encode(buf.getbuffer()).decode("ascii")  
   
@app.route("/")
def main():
    vac_data = get_vaccination_data()
    vacplot_cumul = make_vac_plot_cumul(vac_data)
    vacplot_daily = make_vac_plot_daily(vac_data)
    
    case_data = get_case_data()
    case_plot = make_case_plot(case_data)
    
    bed_data = get_bed_data()
    bed_plot = make_bed_plot(bed_data)
    
    strain_data = get_strain_data()
    strain_plot = make_strain_plot(strain_data)
    
    
    return f'''<h1>Yet another Covid Dashboard!</h1>
    <img width=500px, src='data:image/png;base64,{case_plot}'/>
    <img width=500px, src='data:image/png;base64,{strain_plot}'/>
    <br><br>
    <img width=500px, src='data:image/png;base64,{vacplot_daily}'/>
    <img width=500px, src='data:image/png;base64,{vacplot_cumul}'/>
    <br><br>
    <img width=500px, src='data:image/png;base64,{bed_plot}'/>
    '''
