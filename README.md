# South Bend Public Transportation Analysis
This repository contains scripts and tools designed to investigate the differences between utilization of public transporation and rideshare services in the context of South Bend's Commuters Trust program. The focus is on generating public transporation estimates for existing routes taken by program participants. Movement along these routes is further split into transporation mode such as: _walking, waiting, or riding_. This highlights at what stage time differences are focused.

## Overview
Commuters Trust is a public-private partnership initiated by the City of South Bend to enhance transportation accessibility for residents. Launched in 2019 with support from a $1 million grant from Bloomberg Philanthropies' Mayors Challenge, the program collaborates with local employers and transportation providers to offer subsidized commuting options. Participants receive benefits such as discounted Lyft rides and free Transpo bus passes, aiming to reduce transportation-related employment barriers. 

## Repository Contents
* `main.py`: The primary script that orchestrates data loading, processing, and analysis.
* `stacked_bar_chart_generation.py`: Generates stacked bar charts to visualize various metrics.
* `stacked_bar_chart_generation_hourly.py`: Produces hourly stacked bar charts for detailed temporal analysis.
* `temp_data_processing.py`: Handles preprocessing of raw data for analysis.

## Requirements
To run the scripts in this repository, ensure you have the following Python packages installed:

* `pandas`: For data manipulation and analysis.
* `matplotlib`: For creating visualizations.
* `numpy`: For numerical operations.

You can install these packages using pip:
```
pip install pandas matplotlib numpy
```

## Usage
1. **Data Preparation**: Place the raw data files in the appropriate directory as expected by `temp_data_processing.py`.
2. **Data Processing**: Run `temp_data_processing.py` to preprocess the data.
3. **Analysis**: Execute `main.py` to perform the analysis and generate insights.
4. **Visualization**: Use `stacked_bar_chart_generation.py` and `stacked_bar_chart_generation_hourly.py` to create visual representations of the data.
   
## Contributions
Contributions to enhance the analyses or add new features are welcome. Please fork the repository, make your changes, and submit a pull request for review.

## License
This project is licensed under the MIT License.
