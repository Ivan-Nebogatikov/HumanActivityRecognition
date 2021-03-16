import numpy as np
import pandas as pd
import json
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from datetime import datetime, timedelta
from math import sqrt
from flask import Flask
from flask import request
import json
import time


features = pd.read_csv('c:\\dataset.csv', sep=r'\s*,\s*')
print(features)
activities = list(sorted(set(features['ACT'])))
print("Activities:", activities)

activity_times = {i: timedelta(days=0, seconds=50, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0) for i in activities}
last_activities = list()
current_activity = activities[0]
last_activity_start_date = datetime.now()

states = np.array(features['STATE'])
labels = np.array(features['ACT'])

passive_features = features[features['STATE'] == 'passive']
passive_labels = np.array(passive_features['ACT'])

active_features = features[features['STATE'] == 'active']
active_labels = np.array(active_features['ACT'])

passive_features = passive_features.drop(['ACT', 'STATE'], axis = 1)
active_features = active_features.drop(['ACT', 'STATE'], axis = 1)

base_classifier = RandomForestClassifier(n_estimators=400, random_state=3, class_weight='balanced')
passive_classifier = RandomForestClassifier(n_estimators=400, random_state=3, class_weight='balanced')
active_classifier = KNeighborsClassifier()

def PredictWithHierarcy():
    train_features, test_features, train_labels, test_labels = train_test_split(features, states, test_size=0.25,
                                                                                random_state=242)

    base_classifier.fit(train_features.drop(['ACT', 'STATE'], axis=1), train_labels);

    passive_train_features, passive_test_features, passive_train_labels, passive_test_labels = train_test_split(
        passive_features, passive_labels, test_size=0.25, random_state=242)
    passive_classifier.fit(passive_train_features, passive_train_labels);

    active_train_features, active_test_features, active_train_labels, active_test_labels = train_test_split(
        active_features, active_labels, test_size=0.25, random_state=242)
    active_classifier.fit(active_train_features, active_train_labels);

    t_f = test_features.drop(['ACT', 'STATE'], axis=1)
    pr_states = base_classifier.predict(t_f)
    p_ind = list()
    a_ind = list()
    for i, x in enumerate(pr_states):
        if x == 'passive':
            p_ind.append(i)
        else:
            a_ind.append(i)
    p_s = test_features.iloc[p_ind, :]
    a_s = test_features.iloc[a_ind, :]

    result = 0
    acts = list(set(test_features['ACT']))
    presicionTp = {acts[i]: 0 for i in range(0, len(acts))}
    presicionFp = {acts[i]: 0 for i in range(0, len(acts))}
    p_a = passive_classifier.predict(p_s.drop(['ACT', 'STATE'], axis=1))
    for i in range(0, len(p_a)):
        v = p_s.iloc[i]
        if p_a[i] == v['ACT']:
            result = result + 1
            presicionTp[p_a[i]] = presicionTp[p_a[i]] + 1
        else:
            presicionFp[p_a[i]] = presicionFp[p_a[i]] + 1

    a_a = active_classifier.predict(a_s.drop(['ACT', 'STATE'], axis=1))
    for i in range(0, len(a_a)):
        v = a_s.iloc[i]
        if a_a[i] == v['ACT']:
            result = result + 1
            presicionTp[a_a[i]] = presicionTp[a_a[i]] + 1
        else:
            presicionFp[a_a[i]] = presicionFp[a_a[i]] + 1

    precision = {key: presicionTp[key] / (presicionFp[key] + presicionTp[key]) for key in presicionTp.keys()}

    return result / len(test_features), precision


res = PredictWithHierarcy()
print(res)

def predict(value):
    value = np.array(value).reshape(1, -1)
    base_activity = base_classifier.predict(value)
    if base_activity == 'passive':
        return passive_classifier.predict(value)[0]
    else:
        return active_classifier.predict(value)[0]


print(predict([0, 0, -73, -27])[0])

app = Flask(__name__)


@app.route('/setwarningvalue', methods=['POST'])
def set_warning_value():
    global current_activity, last_activity_start_date
    body = request.json
    activity_times[body['activity']] = timedelta(hours=int(body['hours']), minutes=int(body['minutes']))
    return 'ok'


@app.route('/recognize', methods=['POST'])
def recognize():
    start = round(time.time() * 1000)
    global current_activity, last_activity_start_date
    body = request.json
    act = predict(body['values'])
    last_activities.append(act)
    if len(last_activities) > 5:
        last_activities.pop()
    new_current_activity = max(last_activities, key = last_activities.count)
    status = 'ok'
    if new_current_activity == current_activity:
        if datetime.now() - last_activity_start_date >= activity_times[new_current_activity]:
            status = 'warn'
    else:
        current_activity = new_current_activity
        last_activity_start_date = datetime.now()
    print("Recognize time: " + str(round(time.time() * 1000) - start))
    return json.dumps({'activity': act, 'status': status})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port = 3390)

