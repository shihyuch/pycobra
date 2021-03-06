# Licensed under the MIT License - https://opensource.org/licenses/MIT

from sklearn import linear_model 
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.utils import shuffle
from sklearn.base import BaseEstimator
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
from sklearn.metrics import mean_squared_error

import math
import numpy as np
import random


class Ewa(BaseEstimator):
    """
    Exponential Weighted Average aggregation method.
    """
    def __init__(self, random_state=None):
        """
        Parameters
        ----------
        random_state: integer or a numpy.random.RandomState object. 
            Set the state of the random number generator to pass on to shuffle and loading machines, to ensure
            reproducibility of your experiments, for example.
            
        Attributes
        ----------
        
        machines: A dictionary which maps machine names to the machine objects.
                The machine object must have a predict method for it to be used during aggregation.

        """
        self.machines = {}
        self.random_state = random_state


    def fit(self, X, y, default=True, X_k=None, X_l=None, y_k=None, y_l=None, beta=1.0):
        """
        Parameters
        ----------
        X: array-like, [n_features]
            Training data which will be used to create the Ewa aggregate.

        default: bool, optional
            If set as true then sets up Ewa with default machines and splitting.

        X_k : shape = [n_samples, n_features]
            Training data which is used to train the machines loaded into Ewa. 
            Can be loaded directly into Ewa; if not, the split_data method is used as default.

        y_k : array-like, shape = [n_samples]
            Target values used to train the machines loaded into Ewa.

        X_l : shape = [n_samples, n_features]
            Training data which is used during the aggregation of Ewa.
            Can be loaded directly into Ewa; if not, the split_data method is used as default.

        y_l : array-like, shape = [n_samples] 
            Target values which are actually used in the aggregation of Ewa.
        beta: float, optional
            Parameter to be passed when creating machine weights for EWA.
        """

        X, y = check_X_y(X, y)
        self.X = X
        self.y = y
        self.X_k = X_k
        self.X_l = X_l
        self.y_k = y_k
        self.y_l = y_l

        # set-up Ewa with default machines
        if default:
            self.split_data()
            self.load_default()
            self.load_machine_weights(beta)
        # auto epsilon
        return self


    def split_data(self, k=None, l=None, shuffle_data=False):
        """
        Split the data into different parts for training machines, and for aggregation.

        Parameters
        ----------
        k : int, optional
            k determines D_k, which is the data used to the train the machines.

        l: int, optional
            l determines D_l, which is the data used in the aggregation.

        shuffle: bool, optional
            Boolean value to decide to shuffle the data before splitting.

        """

        if shuffle_data:
            self.X, self.y = shuffle(self.X, self.y, random_state=self.random_state)

        if k is None and l is None:
            k = int(len(self.X) / 2)
            l = int(len(self.X))

        self.X_k = self.X[:k]
        self.X_l = self.X[k:l]
        self.y_k = self.y[:k]
        self.y_l = self.y[k:l]


    def load_default(self, machine_list=['lasso', 'tree', 'ridge', 'random_forest']):
        """
        Loads 4 different scikit-learn regressors by default. 

        Parameters
        ----------
        machine_list: optional, list of strings
            List of default machine names to be loaded. 

        """
        for machine in machine_list:
            if machine == 'lasso':
                self.machines['lasso'] = linear_model.LassoCV(random_state=self.random_state).fit(self.X_k, self.y_k)
            if machine == 'tree':  
                self.machines['tree'] = DecisionTreeRegressor(random_state=self.random_state).fit(self.X_k, self.y_k)
            if machine == 'ridge':
                self.machines['ridge'] = linear_model.RidgeCV().fit(self.X_k, self.y_k)
            if machine == 'random_forest':
                self.machines['random_forest'] = RandomForestRegressor(random_state=self.random_state).fit(self.X_k, self.y_k)


    def load_machine(self, machine_name, machine):
        """
        Adds a machine to be used during the aggregation strategy.
        The machine object must have been trained using X_k and y_k, and must have a 'predict()' method.
        After the machine is loaded, for it to be used during aggregation, load_machine_predictions must be run.

        Parameters
        ----------
        machine_name : string
            Name of the machine you are loading

        machine: machine/regressor object
            The regressor machine object which is mapped to the machine_name

        Returns
        -------
        self : returns an instance of self.
        """
        
        self.machines[machine_name] = machine
        return self


    def load_machine_weights(self, beta):
        """
        Loads the EWA weights for each machine based on the training data.
        Should be run after all the machines to be used for aggregation is loaded.
        Parameters
        ----------
        
        beta : float
            Parameter which controls weights.

        Returns
        -------
        self : returns an instance of self.
        """
        self.machine_MSE = {}
        self.machine_weight = {}
        for machine in self.machines:
            self.machine_MSE[machine] = mean_squared_error(self.y_l, self.machines[machine].predict(self.X_l))
            self.machine_weight[machine] = np.exp((- len(self.y_l) * self.machine_MSE[machine]) / (beta) )

        normalise = sum(self.machine_weight.values(), 0.0)
        self.machine_weight = {k: v / normalise for k, v in self.machine_weight.items() }

        return self


    def predict(self, X):
        """
        Parameters
        ----------
        X: array-like, [n_features]
        """
        X = check_array(X)

        result = 0.0
        for machine in self.machines:
            result += self.machine_weight[machine] * self.machines[machine].predict(X)

        return result


