import __future__ # To standardize all modules imported in this program
from flask import Flask, request, render_template, url_for, redirect # The 
import requests # Python library for making HTTP requests
import matplotlib # Python library for plotting graphs
matplotlib.use('Agg') # To plot and store within server without disturbing the console
import matplotlib.pyplot as plt # Initializing pyplot object within the library
import numpy as np # For handling array values, especially while plotting graphs
from markupsafe import Markup # This module is used for generating HTML markdown codes within python
import time # Time is Money
import os
from dotenv import load_dotenv # For loading credentials into program securely

load_dotenv()

base = "5000" # Port of the Flask server

# Below credentials are necessary for authentication as part of the application team
client_id = os.getenv("CLIENT_ID") # Client ID of the application
client_secret = os.getenv("CLIENT_SECRET") # Client Secret for the application

# URLs are stored here for future use
get_url = "https://www.strava.com/api/v3" # This URL is used for passing requests after authentication
auth_url = "https://www.strava.com/oauth" # This URL is used for the authentication flow.

# Below are credentials that are obtained during the authentication process
auth_code = ""
access_token = ""
refresh_token = ""

# This list used to filter out the necessary data 
filters = ["name", "type", "calories", "description", "distance", "moving_time", "elapsed_time", "average_speed", "max_speed", "has_heartrate"]

# Generates Mock data if user agrees. (Testing purposes only.)
rnd = np.random.RandomState(42)

# Used to generate the contents of the page in the "/stats" route
req = {
    "Recents":{
        "subtitle": "Click to see your recent activities here."
    },
    "Activities":{
        "subtitle": "Manage your activities."
    },
    "Health":{
        "subtitle": "Track your health statistics here."
    }
}

# The fetched JSON data is stored for organized displaying of the data.
jsonData = dict()
activity_ids = []

ignore_case = False
mock_case = False
 
# Flask server initialization
app = Flask(__name__)

# The base route, in this case, 127.0.0.1.5000
@app.route("/")
def index():
    return render_template("index.html", clientId=client_id) # The "Authenticate" button is patched with the authorization link. The client_id is fitted into the link by passing as a parameter (i.e. clientId=client_id)

# The basic error template. If at any point the authentication flow breaks, this page will be shown. This navigates back to the initial page. 
@app.route("/error")
def error():
    return render_template("error.html")

# To handle resource errors that can occur after the authentication process.
@app.route("/resource_error", methods=["GET","POST"])
def resource_error():
    return render_template("resource_error.html")

# This is where the exchanging of the authentication code with the access token takes place. If somewhere the process fails, error page is displayed (done using exception handling mechanism).
@app.route("/success", methods=["GET", "POST"])
def success():
    global auth_code, access_token, refresh_token, jsonData, ignore_case, mock_case
    error = request.args.get('error')
    if error == "access_denied": # The authentication is denied
        return redirect("/error") # Redirected to error page
    
    # Authentication done.

    auth_code = request.args.get('code') # The authentication code is now stored in the server.
    
    
    # The authentication code is exchanged for the access token along with the data.
    response = requests.post(auth_url+"/token", params={"client_id": client_id, "client_secret":client_secret, "code":auth_code, "grant_type":"authorization_code"})
    jsonData = response.json() # The data obtained is stored here.
    try:
        access_token = jsonData["access_token"] # The access token contained in the data is stored in the server.
        refresh_token = jsonData["refresh_token"] # The refresh token contained in the data is stored in the server.
    except KeyError: # Executed if the exchanging of the authentication code with the access token is failed.
        return redirect("/error") # Redirected back to error page
    
    return render_template("success.html")

# Once the authentication process is done, the user is given options to select what kind of data they want to see.
@app.route("/stats", methods=["GET", "POST"])
def stats():
    
    global ignore_case, mock_case # These options are used to get user input on whether they want to see if data is missing or try fitting it with mock data.
    
    gen_component = ""
    
    for data in req:
        gen_component += card(data, req[data]["subtitle"])
    
    gen_component = Markup(gen_component) # Filing details of a component and storing it as a markup object to generate a component
    
    return render_template("stats.html", code=gen_component)

# To display the user on their preference of ignoring or accepting mock data
@app.route("/updated", methods=["GET", "POST"])
def updated():
    
    if not auth_code or not access_token or not refresh_token: # Executes if server restarts.
        return redirect("/error")
    
    global ignore_case, mock_case
    
    form_data = request.form.getlist('check')
    
    ignore_case, mock_case = False, False
    
    for i in form_data:
        if i == 'mock':
            mock_case = True
        if i == 'ignore':
            ignore_case = True
    
    return render_template("updated.html")

# This route is for displaying the activities of an athlete

@app.route("/stats/activities", methods=["GET"])
def activities():
    
    if not auth_code or not access_token or not refresh_token:
        return redirect("/error")
    
    global activity_ids
    
    activity_ids.clear()
    
    response = requests.get(get_url+"/athlete/activities", params={"access_token":access_token})
    gen_component = ""
    if response.status_code >= 400:
        if not ignore_case:
            return redirect("/resource_error")
        else:
            gen_component += null_component() 
    else:
        response = response.json()
        for data in response:
            if activity_ids:
                activity_ids.append(str(data["id"]))
            gen_component += stats_card(data["name"], data["type"], str(data["id"]))
    gen_component = Markup(gen_component)
    return render_template("activities.html", code=gen_component)

# This route shows the health statistics of the athlete

@app.route("/stats/health", methods=["GET", "POST"])
def health():
    
    if not auth_code or not access_token or not refresh_token:
        return redirect("/error")
    
    global ignore_case, mock_case, activity_ids
    
    response = requests.get(get_url + "/athlete/activities", params={"access_token": access_token})
    if response.status_code >= 400:
        if not ignore_case:
            return redirect("/resource_error")
    else:
        response = response.json()
        activity_ids = [str(data["id"]) for data in response]
    
    plt.clf() # Clears all the plots currently inside plt
    gen_component = ""
    fig, ax = plt.subplots(2, 2, figsize=(10, 10))
    ax = ax.flatten()
    i = 0
    gen_component += '''<h4>Health data analysis</h4><div class="card mb-3 col h-50">'''
    for activity_id in activity_ids:
        time_response = requests.get(get_url+"/activities/"+activity_id+"/streams", params={"access_token":access_token, "keys":"time", "key_by_type":"true"})
        if time_response.status_code >= 400:
            if not ignore_case:
                return redirect("/resource_error")
            elif not mock_case:
                gen_component += null_component()
                break
            if mock_case:
                time_response = np.arange(5)
        else:
            time_response = np.array(time_response.json()["data"])
        response = requests.get(get_url+"/activities/"+activity_id+"/streams", params={"access_token":access_token, "keys":"heartrate", "key_by_type":"true"})
        if response.status_code >= 400:
            if not ignore_case:
                return redirect("/resource_error")
            elif not mock_case:
                gen_component += null_component()
                break
            if mock_case:
                response = rnd.randint(70, 120, 5)
        else:
            response = np.array(time_response.json()["data"])
            
        # Plotting graphs for each activity
        
        ax[i].plot(time_response, response)
        ax[i].set_title("Activity ID "+activity_id)
        ax[i].set_xlabel("Time")
        ax[i].set_ylabel("Heart Rate")
            
        i += 1
        if i == 3:
            break

    fig.savefig("static/images/heart.jpg")
    plt.clf()
    
    gen_component += graph_plot("heart", mock_case)+"</div>"
    
    gen_component = Markup(gen_component)
        
    return render_template("health.html", code=gen_component)

# This route is for displaying the Recents Dashboard

@app.route("/stats/recents", methods=["GET"])
def recents():
    
    if not auth_code or not access_token or not refresh_token:
        return redirect("/error")
    
    global ignore_case, mock_case, activity_ids
    
    activity_ids.clear()
    
    athlete_id = ""
    
    activity_response = requests.get(get_url + "/athlete/activities", params={"access_token": access_token})
    if activity_response.status_code >= 400:
        if not ignore_case:
            return redirect("/resource_error")
    else:
        activity_response = activity_response.json()
        activity_ids = [str(data["id"]) for data in activity_response]
    
    response = requests.get(get_url + "/athlete", params={"access_token": access_token})
    if response.status_code >= 400:
        if not ignore_case:
            return redirect("/resource_error")
    else:
        response = response.json()
        athlete_id = str(response["id"])
        
    cards = ""
    
    response = requests.get(get_url + "/athletes/" + athlete_id + "/stats", params={"access_token": access_token})
    if response.status_code >= 400:
        if not ignore_case:
            return redirect("/resource_error")
    response = response.json()
        
    filters = ["all_run_totals", "all_ride_totals", "average_heartrate", "max_speed"]
    
    for filter in filters:
        mock = False
        if filters.index(filter) > 1:
            try:
                l = np.array([data[filter] for data in activity_response])
            except KeyError:
                if mock_case:
                    l = rnd.randint(5, 10, 5)
                    mock = True
                else:
                    cards += null_component()
                    continue
        else:
            try:
                l = np.array(response[filter]["distance"])
            except KeyError:
                if mock_case:
                    l = rnd.randint(5, 10, 5)
                    mock = True
                else:
                    cards += null_component()
                    continue
            
        cards += img_card(filter, processed(filter), str(np.average(l)), mock)
    
    
    cards = Markup(cards)
    
    metrics = ["average_speed", "average_cadence, average_temp", "average_watts", "total_elevation_gain"]
    
    recents = ["recent_run_totals", "recent_ride_totals", "biggest_ride_distance" , "biggest_climb_elevation_gain"]
    
    gen_metric = ""
    
    for metric in metrics:
        try:
            gen_metric += list_metrics(metric, str(np.average(np.array([data[filter] for data in activity_response]))), False)
        except KeyError:
            if mock_case:
                gen_metric += list_metrics(metric, str(rnd.randint(10)), True)
            elif ignore_case:
                gen_metric += null_component()
            else:
                return redirect('/resource_error')
    
    gen_metric = Markup(gen_metric)
    
    gen_recent = ""
    
    for recent in recents:
        mock = True
        try:
            if type(response[recent]) != dict:
                gen_recent += list_metrics(recent, str(response[recent]), False)
            else:
                gen_recent += list_metrics(recent, str(response[recent]["distance"]), False)
        except KeyError:
            if mock_case:
                gen_recent += list_metrics(recent, str(rnd.randint(10)), True)
            elif ignore_case:
                gen_recent += null_component()
            else:
                return redirect('/resource_error')
                
    gen_recent = Markup(gen_recent)
    
    return render_template("recents.html", cards=cards, metrics=gen_metric, recents=gen_recent)

# This route is for displaying the statistics of each activity

@app.route("/stats/activities/each_activity", methods=["GET", "POST"])
def each_activity():
    
    if not auth_code or not access_token or not refresh_token:
        return redirect("/error")
    
    global rnd
    
    activity_id = request.args.get('id')
    activity_name = request.args.get('activity_name')
    response = requests.get(get_url+"/activities/"+activity_id, params={"access_token":access_token, "include_all_efforts":"true"})
    gen_component = ""
    if response.status_code >= 400:
        if not ignore_case:
            return redirect("/resource_error")
        elif not mock_case:
            gen_component += null_component()
    else:
        response = response.json()
        for data in filters:
            gen_component += activity_card(data, str(response[data]))
    keys = ["distance", "velocity_smooth"]
    time_response = requests.get(get_url+"/activities/"+activity_id+"/streams", params={"access_token":access_token, "keys":"time", "key_by_type":"true"})
    gen_component += '''<h4>Performance Analysis</h4><div class="card mb-3 col h-50">'''
    if time_response.status_code >= 400:
        if not ignore_case:
            return redirect("/resource_error")
        elif not mock_case:
            gen_component += null_component()
        if mock_case:
            time_response = np.arange(5)
    else:
        time_response = np.array(time_response.json()["data"])   
    for key in keys:
        response = requests.get(get_url+"/activities/"+activity_id+"/streams", params={"access_token":access_token, "keys":keys, "key_by_type":"true"})
        if response.status_code >= 400:
            if not ignore_case:
                return redirect("/resource_error")
            elif not mock_case:
                gen_component += null_component()
                break
            if mock_case:
                response = rnd.randint(5, 10, 5)
        else:
            response = np.array(response.json()["data"])
        if np.any(time_response) and np.any(response):
            plt.plot(time_response, response)
            plt.savefig("static/images/"+key+".jpg")
            plt.clf()
            gen_component += graph_plot(key, mock_case)
    
    gen_component += "</div>"
    
    gen_component = Markup(gen_component)
    return render_template("each_activity.html", activity_name=activity_name, code=gen_component)


# All the functions below are used to generate components from python to HTML

def stats_card(name, type, ID):
    return '''<div class="bg-warning text-dark card mb-3 col" style="width: 18rem;">
    <div class="bg-warning text-dark m-2 card-body">
    <a class="link-offset-2 link-underline link-underline-opacity-0" href="'''+url_for("each_activity", id=ID, activity_name=name)+'''">
    <h5 class="card-title">''' +name+'''</h5>
    <h6 class="card-subtitle mb-2 text-body-secondary">Type: '''+type+'''</h6>
    <p class="card-subtitle mb-2 text-body-secondary">ID: '''+ID+'''</p>
    </a>
    </div>
    </div>'''
    
def processed(value):
    if value == "calories":
        return "Calories burnt"
    if value == "has_heartrate":
        return "Heart rate noted"
    if value == "heart":
        return "Heart rate"
    if value == "max_speed":
        return "Average max speed"
    value = value.replace("_", " ")
    return value.capitalize()
    

def card(data, subtitle):
    data.replace(" ", "_")
    return '''<div class="bg-warning text-dark card shadow-lg mb-3 col h-50" style="width: 18rem;">
    <a class="link-offset-2 link-underline link-underline-opacity-0" href="'''+url_for(data.lower())+'''">
    <div class="card-body">
    <h5 class="card-title">'''+data+'''</h5>
    <h6 class="card-subtitle mb-2 text-body-secondary">'''+subtitle+'''</h6>
    </a>
    </div>
    </div>'''
    
def activity_card(data, value):
    return '''<div class="card mb-3 col h-50" style="width: 18rem;">
    <div class="card-body">
    <h5 class="card-title">''' +processed(data)+'''</h5>
    <p class="card-subtitle mb-2 text-body-secondary">'''+value+'''</p>
    </a>
    </div>
    </div>'''
    
def graph_plot(name, mock):
    return '''<div class="card text-center m-5 h-50 w-50 gap-2">
    <h5>'''+processed(name)+(" (Mock data)" if mock else "")+'''</h5>
    <img src="'''+(url_for("static", filename="images/"+name+".jpg"))+'''" class="rounded float-none w-50 h-50" alt="'''+name+'''">
    </div>'''

def null_component():
    return '''<div class="container m-3 text-danger">
        <h5>Missing data here</h5>
    </div>'''
    
def img_card(file, what, data, mock):
    return '''<div class="col text-start">
        <div class="card h-25 d-flex flex-row">
            <img src="'''+(url_for("static", filename="images/"+file+".png"))+'''" class="card-img-left img-fluid rounded-start m-2" alt="'''+file+".png"+'''">
                <div class="card-body m-2 text-start" style="height: 200px">
                    <h6 class="card-text fw-medium">'''+what+(" (Mock data)" if mock else "")+'''</h6>
                    <p class="card-text fw-medium">'''+data+'''</p>
                </div>
            </div>
        </div>
    '''
    
def list_metrics(metric, data, mock):
    return '''<li class="list-group-item">
    '''+processed(metric)+(" (Mock data)" if mock else "")+": "+data+'''
    </li>'''
    
    
# The Main function

if __name__ == "__main__":
    app.run(port=base, debug=True)