import json
import os


def get_plan_file(username):

    return f"data/{username}/training_plan.json"


def save_training_plan(username, plan):

    path = get_plan_file(username)

    with open(path,"w") as f:

        json.dump(
            plan,
            f,
            indent=4
        )



def load_training_plan(username):

    path = get_plan_file(username)

    if not os.path.exists(path):
        return None


    with open(path) as f:

        return json.load(f)