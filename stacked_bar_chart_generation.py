import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from main import retrieve_request_time, retrieve_drop_off_time

BUS_DATA_FILE_NAME = "filename.csv"
CT_DATA_FILENAME = "epp_data.csv"
OUTPUT_FILE_NAME = "image.png"


if __name__ == "__main__":
    ### Data Processing ###
    # read data from file
    transit_data = pd.read_csv(BUS_DATA_FILE_NAME)
    rideshare_data = pd.read_csv(CT_DATA_FILENAME)

    # calculations
    rideshare_data["Ride Share - Total Time"] = [retrieve_drop_off_time(rideshare_data, i) - retrieve_request_time(rideshare_data, i) for i, entry in rideshare_data.iterrows() ] #time difference is in seconds, utilizes helper function from main file

    average_transpo_walking_time = transit_data["Time Spent - Walking"].mean()
    average_transit_time = transit_data["Time Spent - Bus"].mean()
    average_transpo_waiting_time = transit_data["Time Spent - Waiting"].mean()

    average_rideshare_transit_time = rideshare_data["Duration (min)"].mean()
    average_rideshare_waiting_time = (rideshare_data["Ride Share - Total Time"].mean() - average_rideshare_transit_time)/60

    #data grouping
    publicTransportData = {"Transit": average_transit_time, "Waiting": average_transpo_waiting_time, "Walking": average_transpo_walking_time} #<2 hr commute time
    rideShareData = {"Transit": average_rideshare_transit_time, "Waiting": average_rideshare_waiting_time, "Walking": 0}

    ### Layer Creation ###
    #Top Layer (All three times)
    tpData = [rideShareData["Transit"] + rideShareData["Waiting"] + rideShareData["Walking"], publicTransportData["Transit"] + publicTransportData["Waiting"] + publicTransportData["Walking"]]
    walkingInput = {"method": ["Ride Share", "Public Transit"], "times": tpData}

    #Middle Layer
    midData = [rideShareData["Transit"] + rideShareData["Waiting"], publicTransportData["Transit"] + publicTransportData["Waiting"]]
    waitingInput = {"method": ["Ride Share", "Public Transit"], "times": midData}

    #Bottom Layer
    btmData = [rideShareData["Transit"], publicTransportData["Transit"]]
    transitInput = {"method": ["Ride Share", "Public Transit"], "times":btmData}

    ### Chart Creation ###
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

    plt.savefig(OUTPUT_FILE_NAME)
    plt.show()