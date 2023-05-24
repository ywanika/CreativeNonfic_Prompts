from flask import Flask, render_template, redirect, request, session
import os
from flask_pymongo import PyMongo

app = Flask(__name__) #__name__  is set by python
app.debug = True

#gets connectection string for Mongo DB
if os.getenv("MONGO_URI") == None :
    file = open("connection_string.txt","r")
    connection_string = file.read().strip()
    app.config['MONGO_URI']=connection_string
else:
    app.config['MONGO_URI']= os.getenv("MONGO_URI")

#gets secret key for session
if os.getenv("SECRET_KEY") == None :
    app.config["SECRET_KEY"] = "gguu"
else:
    app.config["SECRET_KEY"]= os.getenv("SECRET_KEY")

mongo = PyMongo(app)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        fullPrompt = list(mongo.db.finalPrompts.find().limit(1).sort("$natural", -1))
        session.clear()
        if fullPrompt == []:
            return render_template ("home.html", currentPrompt = "No Current Prompt", currentSubmissions = [])
        currentPrompt = fullPrompt[0]["prompt"]
        submissions = list(mongo.db.submissions.find({"prompt":currentPrompt})) #list of dictionaries
        currentSubmissions={}
        for submission in submissions:
            currentSubmissions[ submission["name"] ] = submission["piece"]
        return render_template ("home.html", currentPrompt = currentPrompt, currentSubmissions = currentSubmissions)
        
    else:
        fullPrompt = list(mongo.db.finalPrompts.find().limit(1).sort("$natural", -1))
        if fullPrompt == []:
            return render_template ("home.html", currentPrompt = "!!Not Submitted, Wait until prompt!!")
        currentPrompt = fullPrompt[0]["prompt"]
        name = request.form["name"]
        piece = request.form["piece"]
        mongo.db.submissions.insert_one({"prompt": currentPrompt, "name": name, "piece": piece})
        return redirect("/")

        

@app.route("/allSubmissions")
def past():
    allSubmissionsDB = list(mongo.db.submissions.find()) #list of dictionaries
    prompts = set()
    for submission in allSubmissionsDB:
        prompts.add(submission["prompt"])
    allSubmissions = {}
    for prompt in prompts:
        submissionsInPrompt = list(mongo.db.submissions.find({"prompt": prompt}))
        submissions = {}
        for submission in submissionsInPrompt:
            submissions[ submission["name"] ] = submission["piece"]
        allSubmissions[prompt] = submissions
        
    return render_template ("allSubmissions.html", allSubmissions = allSubmissions)

@app.route("/adminLogin", methods = ["GET", "POST"])
def adminLogIn():
    if request.method == "GET":
        return render_template ("adminLogin.html")
    else:
        username = request.form["username"]
        user_data = mongo.db.adminUsers.find_one({"username":username})
        if user_data != None:
            return redirect("/choosePrompt?username="+username)
        return render_template("adminLogin.html", message = "try again")

@app.route("/choosePrompt", methods = ["GET", "POST"])
def choosePrompt():
    if request.method == "GET":
        username = request.args.get("username")
        user_data = mongo.db.adminUsers.find_one({"username":username})
        if user_data != None:
            session["user"] = username
            essayRecords = mongo.db.EssayPrompts.aggregate([ {"$match":{"usageCount": {"$in": [0, 1]}}}, {"$sample":{ "size": 1 }} ])
            essay = next(essayRecords)["prompt"]
            subjectRecords = mongo.db.SubjectPrompts.aggregate([ {"$match":{"usageCount": {"$in": [0, 1]}}}, {"$sample":{ "size": 1 }} ])
            subject = next(subjectRecords)["prompt"]
            return render_template ("choosePrompt.html", essayPrompt = essay, subjectPrompt = subject)
    else:
        button = request.form["button"]
        if button == "New Prompt":
            if "user" in session:
                username = session["user"]
                return redirect("/choosePrompt?username="+username)
            else:
                return redirect("/adminLogin")
        elif button == "Select":
            essay = request.form["essayPrompt"]
            subject = request.form["subjectPrompt"]
            mongo.db.EssayPrompts.find_one_and_update({"prompt":essay}, {"$inc":{"usageCount":1}})
            mongo.db.SubjectPrompts.find_one_and_update({"prompt":subject}, {"$inc":{"usageCount":1}})
            fullPrompt = f"Write a {essay} with the prompt: {subject}"
            mongo.db.finalPrompts.insert_one({"prompt":fullPrompt})
            return redirect("/")

if __name__ == "__main__":
    app.run()
