import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from main import retrieve_request_time, retrieve_drop_off_time


if __name__ == "__main__":
    transit_data = pd.read_csv("Time Splits - All (2023) (less than 200m).csv")
    rideshare_data = pd.read_csv("Data\\EPP_Uber_2023.csv")

    rideshare_data["Ride Share - Total Time"] = [retrieve_drop_off_time(rideshare_data, i) - retrieve_request_time(rideshare_data, i) for i, entry in rideshare_data.iterrows() ]

    average_transpo_walking_time = transit_data["Time Spent - Walking"].mean()
    average_transit_time = transit_data["Time Spent - Bus"].mean()
    average_transpo_waiting_time = transit_data["Time Spent - Waiting"].mean()


    average_rideshare_transit_time = rideshare_data["Duration (min)"].mean()
    average_rideshare_waiting_time = (rideshare_data["Ride Share - Total Time"].mean() - average_rideshare_transit_time)/60

    #publicTransportData = {"Transit": 24, "Waiting": 205, "Walking": 23} #all inclusive data
    publicTransportData = {"Transit": average_transit_time, "Waiting": average_transpo_waiting_time, "Walking": average_transpo_walking_time} #<2 hr commute time
    rideShareData = {"Transit": average_rideshare_transit_time, "Waiting": average_rideshare_waiting_time, "Walking": 0}

    #Top Layer (All three times)
    tpData = [rideShareData["Transit"] + rideShareData["Waiting"] + rideShareData["Walking"], publicTransportData["Transit"] + publicTransportData["Waiting"] + publicTransportData["Walking"]]
    walkingInput = {"method": ["Ride Share", "Public Transit"], "times": tpData}

    #Middle Layer
    midData = [rideShareData["Transit"] + rideShareData["Waiting"], publicTransportData["Transit"] + publicTransportData["Waiting"]]
    waitingInput = {"method": ["Ride Share", "Public Transit"], "times": midData}

    #Bottom Layer
    btmData = [rideShareData["Transit"], publicTransportData["Transit"]]
    transitInput = {"method": ["Ride Share", "Public Transit"], "times":btmData}

    sns.set_theme(style="darkgrid")
    plt.figure(figsize=(14, 14))

    ax1 = bar1 = sns.barplot(x="method", y="times", data=walkingInput, color='darkblue')
    bar2 = sns.barplot(x="method", y="times", data=waitingInput, color='lightblue')
    bar3 = sns.barplot(x="method", y="times", data=transitInput, color='mediumspringgreen')

    top_bar = mpatches.Patch(color='darkblue', label='Walking (mins)')
    mid_bar = mpatches.Patch(color='lightblue', label='Waiting (mins)')
    bottom_bar = mpatches.Patch(color='mediumspringgreen', label='Transit (mins)')
    plt.legend(handles=[top_bar, mid_bar, bottom_bar])

    plt.title("Transit Times")
    plt.ylabel("Minutes")
    plt.xlabel("Transportation Method")

    #ax1.bar_label(ax1.containers[0])
    #plt.savefig("Transit Times Stacked (below 2hr transit time).png")
    plt.savefig("Transit Times Stacked (All)(2023)(less than 200m).png")
    plt.show()