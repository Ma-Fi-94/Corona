# YACD (Yet Another Covid Dashboard)
My first attempt at a web app using flask. Shows plots of Covid case numbers, vaccination numbers and intensive care beds over time for Germany.

Check it out "in production" here https://covid-dashboard-mmf.herokuapp.com/ .

Or run it locally on your own machine by executing *run.sh* .

Preview:

![](https://github.com/Ma-Fi-94/YACD/blob/main/screen.png)

## How it works
Data on Covid cases, vaccinations, and intensive care beds is queried from the authorities' web pages using pandas. The data is kept in a cache for 30 minutes to avoid sending out too many requests. Plots are generated from the data using matplotlib, and saved as base64-strings. Those are then placed inside a HTML string that's exposed to the web using flask.
