import requests
import pandas as pd
from time import sleep

PROGRESS_FILE_NAME = "temp_transit_duration.csv"
RIDES_FILE_NAME = "EPP_Uber_Rides_2024.csv"
API_KEY_FILE_NAME = "api-key.txt"
HOME_TO_SCHOOL = {"Start": (41.525,-87.507), "End": (41.555,-87.335)}
EPP_EXAMPLE = {"Start": (41.691,-86.181), "End": (41.704,-86.236)}
API_CALL_RATE = 25 #per second

#TO DO:
# Have API call rate check on time pass rather than waiting a set time.
# Have script check for existence of bad coordinates file. If it is there create a new file.
# add a time out function for requests
# add the functionality to determine what requests still need to be made/have been made


def encode_endpoints (start_coords: tuple, end_coords: tuple) -> str :
    """Formats coordinates for inclusion in request url."""
    origin = f"origin={start_coords[0]},{start_coords[1]}"
    destination = f"destination={end_coords[0]},{end_coords[1]}"

    return f"{origin}&{destination}"


def construct_request(coordinates: dict, api_key: str) -> str:
    """Creates the request used to retrieve route recommendations from Google."""
    endpoints = encode_endpoints(coordinates["Start"], coordinates["End"])
    mode =  "mode=transit"
    request_url = f"https://maps.googleapis.com/maps/api/directions/"
    output_format = "json"
    request_url += f"{output_format}?{endpoints}&key={api_key}&{mode}"

    return request_url


def retrieve_rides(filename: str) -> list:
    """Retrieve all start & end coordinates from EPP data file."""
    rides_df = pd.read_csv(filename)
    ride_coords = []
    for i in range(rides_df.shape[0]):
        start_lat = rides_df.iloc[i]["Pickup Latitude"]
        start_long = rides_df.iloc[i]["Pickup Longitude"]
        end_lat = rides_df.iloc[i]["Drop Off Latitude"]
        end_long = rides_df.iloc[i]["Drop Off Longitude"]
        id = rides_df.iloc[i]["ID"]
        

        route_coords = {"Start": (start_lat, start_long), "End": (end_lat,end_long), "ID": id}
        ride_coords.append(route_coords)

    return ride_coords


def pool_data(rides: list):
    """Pool data into dictionary format to construct final dataframe."""
    ids = []
    start_lats = []
    start_longs = []
    end_lats = []
    end_longs = []
    durations = []
    for ride in rides:
        if "Transit Duration" in ride:
            ids.append(ride["ID"])
            start_lats.append(ride["Start"][0])
            start_longs.append(ride["Start"][1])
            end_lats.append(ride["End"][0])
            end_longs.append(ride["End"][1])
            durations.append(ride["Transit Duration"])

    df_input = {"ID": ids,
                "Pickup Latitude": start_lats,
                "Pickup Longitude": start_longs,
                "Drop Off Latitude": end_lats,
                "Drop Off Longitude": end_longs,
                "Transit Duration": durations}

    duration_df = pd.DataFrame(df_input)

    return duration_df


def add_transit_duration(rides, api_key):
    """Retrieves quickest public transportation directions from Google API. Duration is added to rides dictionary."""
    for ride in rides:
        request_url = construct_request(ride, api_key)
        transit_route = requests.get(request_url)

        sleep(1/API_CALL_RATE)

        if ride["Start"] == ride["End"]:
            with open("bad coordinates.txt", "a+") as file:
                file.write("Bad coordinates at ID:" + str(ride["ID"]) + '\n')
                file.write(request_url + '\n')

            print("Bad coordinates at ID:", ride["ID"])
            print(request_url)
            continue

        json = transit_route.json()
        try:
            if check_transit_mode(json): #ensures no driving directions were given
                ride["Transit Duration"] = json["routes"][0]["legs"][0]["duration"]["text"]
                print(str(ride["ID"]) + ":", ride["Transit Duration"])

                with open(PROGRESS_FILE_NAME, "a+") as file:
                    temp_data = str(ride["ID"]) + ","
                    temp_data += ride["Transit Duration"] + "\n"
                    file.write(temp_data)

            else:
                print("Route:", ride["ID"], "was provided driving directions.")
                print(request_url)

        except:
            print("No route at ID:", ride["ID"])
            # print(request_url)
            with open("bad coordinates.txt", "a+") as file:
                file.write("No route at ID:" + str(ride["ID"]) + '\n')
                file.write(request_url + '\n')


    return rides


def test():
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    request_url = construct_request(HOME_TO_SCHOOL, api_key)
    print(request_url)
    route = requests.get(request_url)
    duration = route.json()["routes"][0]["legs"][0]["duration"]["text"]
    print(duration)


def check_transit_mode(json):
    """Checks the direction type given by api call."""
    for step in json["routes"][0]["legs"][0]["steps"]:
        if step["travel_mode"] == "DRIVING":
            return False
    return True


def calculate_request_time()->int:
    pass


def create_error_record():
    pass

def retrieve_api_key(file_name: str) -> str:
    """Retrieves the contents of the specified file."""
    api_key = ""
    with open(file_name, "r") as file:
        api_key = file.read()
    return api_key



if __name__ == "__main__":
    api_key = retrieve_api_key(API_KEY_FILE_NAME)
    # request_url = construct_request(EPP_EXAMPLE)
    # route = requests.get(request_url)
    # print(request_url)
    # json = route.json()

    all_rides = retrieve_rides(RIDES_FILE_NAME)
    all_rides = add_transit_duration(all_rides, api_key)
    #
    transit_duration_df = pool_data(all_rides)
    transit_start_df = transit_duration_df[["ID", "Pickup Latitude", "Pickup Longitude", "Transit Duration"]]
    transit_end_df = transit_duration_df[["ID", "Drop Off Latitude", "Drop Off Longitude", "Transit Duration"]]
    transit_start_df.to_csv("Transit_Duration_Start_Coords v1.csv")
    transit_end_df.to_csv("Transit_Duration_End_Coords v1.csv")
