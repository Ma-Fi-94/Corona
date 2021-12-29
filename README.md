# YACD (Yet Another Covid Dashboard)
My first attempt at a web app using flask. Shows plots of Covid case numbers, vaccination numbers and intensive care beds over time for Germany.

![](https://github.com/Ma-Fi-94/YACD/blob/main/scr.png)

## How it works
Data on Covid cases, vaccinations, and intensive care beds is queried from the authorities' web pages using pandas. Plots are then generated using matplotlib and saved as base64-strings. Those are then placed inside a HTML string that's exposed to the web using flask.

## To Be Done
-Make the HTML aesthetically more pleasing by using some basic CSS (background colour, fonts, etc.).
-Maybe cache the data to avoid too frequent polling?
