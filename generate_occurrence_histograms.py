import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt

INPUT_FILE_NAME_2023 = "2023_data.csv"
INPUT_FILE_NAME_2024 = "2024_data.csv"
OUTPUT_FILE_NAME = "output file name"

if __name__ == "__main__":
    # Data Input
    dataDF2023 = pd.read_csv(INPUT_FILE_NAME_2023)
    dataDF2024 = pd.read_csv(INPUT_FILE_NAME_2024)

    # Data Processing
    dataDFBoth = pd.concat([dataDF2023, dataDF2024])
    dataDFBothBelow200 = dataDFBoth[dataDFBoth["Transit Duration"] <= 200]

    #Plot Creation (All Data)
    sns.set_style("whitegrid")
    plt.title("Distribution - Public Transportation Estimates (All)", fontsize=14)
    plt.ylabel("Occurrences", fontsize=12)
    plt.xlabel("Duration (mins)", fontsize=12)

    sns.histplot(data=dataDFBoth["Transit Duration"], bins=16)
    plt.savefig(OUTPUT_FILE_NAME + "(All)" + ".png")
    plt.clf()

    # Plot Creation (Tail Removed)
    plt.title("Distribution - Public Transportation Estimates (Trimmed)", fontsize=14)
    plt.ylabel("Occurrences", fontsize=12)
    plt.xlabel("Duration (mins)", fontsize=12)
    sns.set_style("whitegrid")

    sns.histplot(data=dataDFBothBelow200["Transit Duration"], bins=16)
    #plt.savefig(OUTPUT_FILE_NAME + "(Trimmed)" + ".png")
