# South Bend Public Transportation Analysis
This repository contains scripts and tools designed to analyze public transportation data for South Bend, Indiana. The analyses focus on understanding various aspects of the South Bend Public Transportation Corporation (Transpo) system, including ridership patterns, route performance, and service efficiency.

## Overview
Transpo serves the South Bend and Mishawaka metropolitan area, operating fixed-route bus services and paratransit services. The system comprises 20 routes, connecting key locations such as downtown South Bend, Mishawaka, and the University of Notre Dame. 

## Repository Contents
main.py: The primary script that orchestrates data loading, processing, and analysis.
stacked_bar_chart_generation.py: Generates stacked bar charts to visualize various metrics.
stacked_bar_chart_generation_hourly.py: Produces hourly stacked bar charts for detailed temporal analysis.
temp_data_processing.py: Handles preprocessing of raw data for analysis.

## Requirements
To run the scripts in this repository, ensure you have the following Python packages installed:

pandas: For data manipulation and analysis.
matplotlib: For creating visualizations.
numpy: For numerical operations.
You can install these packages using pip:
'''
pip install pandas matplotlib numpy
'''

## Usage
1. Data Preparation: Place the raw data files in the appropriate directory as expected by temp_data_processing.py.
2. Data Processing: Run temp_data_processing.py to preprocess the data.
3. Analysis: Execute main.py to perform the analysis and generate insights.
4. Visualization: Use stacked_bar_chart_generation.py and stacked_bar_chart_generation_hourly.py to create visual representations of the data.
   
## Contributions
Contributions to enhance the analyses or add new features are welcome. Please fork the repository, make your changes, and submit a pull request for review.

## License
This project is licensed under the MIT License.
