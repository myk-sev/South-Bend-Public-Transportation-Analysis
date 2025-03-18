import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

BUS_DATA_FILE_NAME = "filename.csv"
OUTPUT_FILE_NAME = "image.png"


if __name__ == "__main__":
    ### Data Processing ###
    # read data from file
    data = pd.read_csv(BUS_DATA_FILE_NAME)

    # calculations
    byHour = {hour: df for hour, df in data.groupby("Hour")}
    averageTimes = {}
    for hour in byHour:
        averageTimes[hour] = {
            "Walking": byHour[hour]["Time Spent - Walking"].mean(),
            "Bus": byHour[hour]["Time Spent - Bus"].mean(),
            "Waiting": byHour[hour]["Time Spent - Waiting"].mean()
        }

    ### Layer Creation ###
    # Bottom Layer
    bottomData = [averageTimes[hour]["Bus"] for hour in range(24)]
    transitInput = {"hour": [i for i in range(24)], "times": bottomData}

    # Middle Layer
    middleData = [bottomData[hour] + averageTimes[hour]["Waiting"] for hour in range(24)]
    waitingInput = {"hour": [i for i in range(24)], "times": middleData}

    #Top Layer (All three times)
    topData = [bottomData[hour] + middleData[hour] + averageTimes[hour]["Walking"] for hour in range(24)]
    walkingInput = {"hour": [i for i in range(24)], "times": topData}

    ### Chart Creation ###
    sns.set_theme(style="darkgrid")
    plt.figure(figsize=(14, 14))

    ax1 = bar1 = sns.barplot(x="hour", y="times", data=walkingInput, color='darkblue')
    bar2 = sns.barplot(x="hour", y="times", data=waitingInput, color='lightblue')
    bar3 = sns.barplot(x="hour", y="times", data=transitInput, color='mediumspringgreen')

    top_bar = mpatches.Patch(color='darkblue', label='Walking (mins)')
    mid_bar = mpatches.Patch(color='lightblue', label='Waiting (mins)')
    bottom_bar = mpatches.Patch(color='mediumspringgreen', label='Transit (mins)')
    plt.legend(handles=[top_bar, mid_bar, bottom_bar])

    plt.title("Transit Time Split by Hour")
    plt.ylabel("Minutes")
    plt.xlabel("Hour")

    plt.savefig(OUTPUT_FILE_NAME)
    plt.show()