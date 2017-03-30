from process_data import extract_features, process_links, geojson_link, \
    process_trips, process_net, process_node, array_to_trips, process_results, output_file
# from frank_wolfe import solver, solver_2, solver_3
import numpy as np
from metrics import average_cost, cost_ratio, cost, save_metrics
# from heterogeneous_solver import gauss_seidel, jacobi
from multi_types_solver import parametric_study
from utils import multiply_cognitive_cost, heterogeneous_demand


def load_I210():
    net = np.loadtxt('data/I210_net.csv', delimiter=',', skiprows=1)
    demand = np.loadtxt('data/I210_od.csv', delimiter=',', skiprows=1)
    node = np.loadtxt('data/I210_node.csv', delimiter=',', skiprows=1)
    geometry = extract_features('data/I210Sketch_net.csv')
    demand = np.reshape(demand, (1, 3))
    return net, demand, node, geometry


def process_I210_net():
    process_net('data/I210Sketch_net.csv', 'data/I210_net.csv')


def frank_wolfe_on_I210():
    '''
    Frank-Wolfe on I210
    '''
    graph = np.loadtxt('data/I210_net.csv', delimiter=',', skiprows=1)
    demand = np.loadtxt('data/I210_od.csv', delimiter=',', skiprows=1)
    demand[:, 2] = 1. * demand[:, 2] / 4000
    # run solver
    f = solver_3(graph, demand, max_iter=1000, q=50, display=1, stop=1e-2)
    # display cost
    for a, b in zip(cost(f, graph), f * 4000):
        print a, b
    # visualization
    node = np.loadtxt('data/I210_node.csv', delimiter=',', skiprows=1)
    # extract features: 'capacity', 'length', 'fftt'
    feat = extract_features('data/I210Sketch_net.csv')
    ratio = cost_ratio(f, graph)
    # merge features with the cost ratios
    features = np.zeros((feat.shape[0], 4))
    features[:, :3] = feat
    features[:, 3] = ratio
    # join features with (lat1,lon1,lat2,lon2)
    links = process_links(graph, node, features)
    color = features[:, 3]  # we choose the costs
    names = ['capacity', 'length', 'fftt', 'tt_over_fftt']
    geojson_link(links, names, color)


def I210_ratio_r_total():
    '''
    study the test_*.csv files generated by I210_parametric_study()
    in particular, visualize the ratio each type of users on each link
    '''
    fs = np.loadtxt('data/test_50.csv', delimiter=',', skiprows=0)
    ratio = np.divide(fs[:, 1], np.maximum(np.sum(fs, axis=1), 1e-8))
    net = np.loadtxt('data/I210_net.csv', delimiter=',', skiprows=1)
    node = np.loadtxt('data/I210_node.csv', delimiter=',', skiprows=1)
    geometry = extract_features('data/I210Sketch_net.csv')
    features = np.zeros((fs.shape[0], 4))
    features[:, :3] = geometry
    features[:, 3] = ratio
    links = process_links(net, node, features)
    color = 2 * ratio  # we choose the ratios of nr over r+nr
    geojson_link(links, ['capacity', 'length', 'fftt', 'r_routed'], color)
    # print(fs)
    # for a,b in zip(cost(f, graph), f*4000): print a,b


def I210_parametric_study(alphas):
    g, d, node, geom = load_I210()
    d[:, 2] = d[:, 2] / 4000.
    parametric_study(alphas, g, d, node, geom, 3000., 100.,
                     'data/I210/test_{}.csv', stop=1e-3, stop_cycle=1e-3)


def I210_metrics(alphas):
    net, d, node, features = load_I210()
    d[:, 2] = d[:, 2] / 4000.
    net2, small_capacity = multiply_cognitive_cost(net, features, 3000., 100.)
    save_metrics(alphas, net, net2, d, features, small_capacity,
                 'data/I210/test_{}.csv', 'data/I210/out.csv', skiprows=1)


def I210_path_choices(alphas):
    out = np.zeros((len(alphas), 4))
    for i, alpha in enumerate(alphas):
        f_r = np.loadtxt('data/I210/test_{}.csv'.format(int(alpha * 100)), delimiter=',',
                         skiprows=1)[:, 1]
        out[i, 0] = alpha
        if f_r[12] > 0.:
            out[i, 3] = f_r[12] * 4000.  # flow middle path
        if f_r[0] > 0.:
            out[i, 2] = f_r[0] * 4000.  # flow up path
        if f_r[13] > 0.:
            out[i, 1] = f_r[13] * 4000.  # flow low path
    np.savetxt('data/I210/path_flows_routed.csv', out, delimiter=',',
               header='ratio_routed,low_path,hi_path,mid_path', comments='')


def check_results():
    # check highest ration of tt / fftt (should be less than 5)
    net, d, node, features = load_I210()
    f = np.loadtxt('data/I210/test_0.csv', delimiter=',')
    print np.max(cost_ratio(f, net))


def I210_ratio_r_nr(alpha):
    '''
    study the test_*.csv files generated by chicago_parametric_study()
    in particular, visualize the ratio each type of users on each link

    #ratio of non-routed over total for each link 
    '''
    fs = np.loadtxt(
        'data/I210/test_{}.csv'.format(int(alpha * 100)), delimiter=',', skiprows=0)
    ratio = np.divide(fs[:, 1], np.maximum(np.sum(fs, axis=1), 1e-8))

    net, demand, node, geometry = load_I210()
    features = np.zeros((fs.shape[0], 4))
    features[:, :3] = geometry
    features[:, 3] = ratio

    links = process_links(net, node, features, in_order=True)
    color = 5. * ratio  # we choose the ratios of nr over r+nr
    geojson_link(links, ['capacity', 'length', 'fftt', 'r_non_routed'], color)


def visual(alpha):
    '''
    study the test_*.csv files generated by chicago_parametric_study()
    in particular, visualize the ratio each type of users on each link

    #ratio of non-routed over total for each link 
    '''
    fs = np.loadtxt(
        'data/I210/test_{}.csv'.format(int(alpha * 100)), delimiter=',', skiprows=0)

    f_total = 4000 * np.sum(fs, axis=1)
    color = np.zeros(len(f_total))

    v_max = 30000
    v_thres = 6000

    for i in range(len(f_total)):
        if f_total[i] <= v_thres:
            color[i] = 1
        # elif f_total[i]<=2*v_thres:
        #     color[i]=2
        # elif f_total[i]<=3*v_thres:
        #     color[i]=3
        # elif f_total[i]<=4*v_thres:
        #     color[i]=4
        else:
            color[i] = 5

    print(np.mean(color))

    net, demand, node, geometry = load_I210()
    features = np.zeros((fs.shape[0], 4))
    features[:, :3] = geometry
    features[:, 3] = f_total

    links = process_links(net, node, features, in_order=True)
    # color = 5. * ratio # we choose the ratios of nr over r+nr
    geojson_link(links, ['capacity', 'length', 'fftt', 'r_non_routed'], color)


def I210_capacities():
    net, demand, node, features = load_I210()
    links = process_links(net, node, features)
    color = 2. * (features[:, 0] <= 3000.) + 5. * (features[:, 0] > 3000.)
    weight = (features[:, 0] <= 3000.) + 2. * (features[:, 0] > 3000.)
    geojson_link(links, ['capacity', 'length', 'fftt'], color, 2. * weight)


def main():
    # process_I210_net()
    # frank_wolfe_on_I210()
    # I210_parametric_study()
    # I210_ratio_r_total()
    # I210_parametric_study_2()
    I210_parametric_study(np.linspace(0, .25, 26))
    I210_metrics(np.linspace(0, .25, 26))
    # 210_ratio_r_nr(0.9)
    # visual(0.5)
    # check_results()
    # I210_path_choices(np.linspace(0,.25,26))
    # I210_capacities()


if __name__ == '__main__':
    main()
