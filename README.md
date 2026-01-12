This project is an edited and expanded version of [Bill Fitzgerald's Get-the-990](https://github.com/billfitzgerald/get_the_990/tree/main). I added in the creation of financial ratios, year-to-year financial comparisons, and created a simple graphical user interface to load in a csv with XML links and choose the output destination of the parsed files.

It has been tested and works on both MacOS and Windows. 
I will be adding features and expanding on this tool as I use it for research.

# How to use 990 Decoder: 

1. Download the latest release from the "release" page on GitHub.
2. After unzipping the file on Mac or downloading the .exe on Windows, you can open the program.
   NOTE: On Mac, the program may get flagged as a security risk, since it was downloaded from the internet. You will need to go to Settings-> Privacy & Security, and scroll down. There, you will see the 990 Decoder flagged and an option to "open anyway".
4. The 990 Decoder accepts a .csv file of links to ProPublica's .xml 990 forms. Go to ProPublica's Non-Profit explorer page, find your Non-Profit, and for every year's 990 form, right-click the button that says "XML", hit "Copy Link". Paste it into a .csv file. As of v1.0.01, the first line of the .csv file NEEDS to just say "source," otherwise the decoder will return an error code. Every following line should be a link to the .xml file. You can compile these links in Excel or Google sheets, just make sure to save/export the file as a .csv, and not .xlsx. 
5. Select a destination folder. This is where the parsed data will be returned. 
6. Hit "Run parser"
7. Wherever you specified the output file, there will be an overview HTML file, one for basic financial calculations, one that summarizes people associated with the organization, and, importantly, one that automatically computes year-to-year financial ratios for the nonprofit. In the financial ratio output document, there will also be a row that computes ratios between the earliest 990 you included and the most recent one. For example, if I upload 990 forms for every year between 2018 and 2024, then there will be a row that computes financial ratios between the data in the 2018 990, and the 2024 990. So keep that in mind in case you want to compute a specific range! 

Of course, if you are using this tool for any kind of decision making, you should double-check the calculations yourself. This is a tool mainly intended to reduce the amount of menial labor involved with flipping through different .pdfs so that power researchers can focus their time and energy on more important questions.

From Bill's original ReadMe:

# 1. Summarize data from Form 990s

Parse and summarize data from ProPublica's NonProfit Explorer at https://projects.propublica.org/nonprofits/

All nonprofits are required to submit Form 990s. These forms contain interesting information, but it's often buried deep in the report, and it's hard to dig out.

Additionally, it's not easy to compare multiple forms side by side (ie, you want to compare one org across multiple years, or you want to compare two or more orgs).

If you are doing research into nonprofits, **Get the 990** is for you!

# 2. Features

**Get the 990** uses data shared and maintained in ProPublica's Nonprofit Explorer. ProPublica shares the data in multiple formats, including PDF downloads and via XML. **Get the 990** uses the XML to pull out a subset of data from the Form 990.

# 3. Intended Use Case

**Get the 990** is best used as a preliminary research tool. It is designed to be a starting point to help surface areas that look like they merit additional research. As we have all experienced, researching companies can lead us down rabbit holes. **Get the 990** is intended to make those rabbit holes easier to spot and avoid (or at least make them more shallow).

# 4. Plans and Next Steps

**Get the 990** just scratches the surface of the data that's in a Form 990. The roadmap includes pulling out data on donations to nonprofits, and funding issued by nonprofits.

Pull requests are welcome, as are issues and questions.

# 5. Technical Details

**Get the 990** requires Python 3.6 or higher.
