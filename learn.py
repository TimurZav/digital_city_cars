from environment import Env
from keras import Sequential, layers
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox

dt = 1 / 1000
N = 33

"""Lower Manhattan"""
# G = ox.load_graphml('lowermanhattan.graphml')
# G = ox.project_graph(G)
# fig, ax = ox.plot_graph(G, node_size=0, edge_linewidth=0.5)

"""San Francisco"""
# G = ox.load_graphml('sanfrancisco.graphml')
# G = ox.project_graph(G)
# fig, ax = ox.plot_graph(G, node_size=0, edge_linewidth=0.5)

"""Piedmont, California"""
G = ox.load_graphml('piedmont.graphml')
G = ox.project_graph(G)
fig, ax = ox.plot_graph(G, node_size=0, edge_linewidth=0.5)

# grab the dimensions of the figure
axis = ax.axis()

""" which car to be the learning agent is chosen here ---> agent=1 """
# initialize the environment for the learning agent
env = Env(n=N, fig_axis=axis, agent=6)

# initialize the Keras training model
model = Sequential()
model.add(layers.InputLayer(batch_input_shape=(1, 10)))
model.add(layers.Dense(10, activation='sigmoid'))
model.add(layers.Dense(2, activation='linear'))
model.compile(loss='mse', optimizer='adam', metrics=['mae'])

# now execute Q learning
y = 0.95
eps = 0.5
decay_factor = 0.999
r_avg_list = []
num_episodes = 10

for i in range(num_episodes):
    print("Episode {} of {}".format(i + 1, num_episodes))
    state = env.reset()
    eps *= decay_factor
    done = False
    r_sum = 0
    while not done:
        if np.random.random() < eps:
            action = np.random.randint(0, 2)
        else:
            action = np.argmax(model.predict(np.identity(10)[state:state + 1]))
        new_s, r, done, _ = env.step(action=action, num=i)
        target = r + y * np.max(model.predict(np.identity(10)[new_s:new_s + 1]))
        target_vec = model.predict(np.identity(10)[state:state + 1])[0]
        target_vec[action] = target
        model.fit(np.identity(10)[state:state + 1], target_vec.reshape(-1, 2), epochs=1, verbose=0)
        state = new_s
        r_sum += r
    r_avg_list.append(r_sum / num_episodes)


plt.plot(np.arange(num_episodes), r_avg_list)
plt.xlabel('Game number')
plt.ylabel('Average reward per game')
plt.show()


