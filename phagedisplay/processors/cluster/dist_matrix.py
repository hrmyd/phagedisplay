__description__ = \
"""
Classes for creating distance matrices between sets of aligned sequence data.
"""
__author__ = "Hiranmayi Duvvuri, Michael J. Harms"
__date__ = "2016-04-06"

import numpy as np
import random 
import scipy
from scipy import spatial

import pandas as pd

try:
    import jellyfish as jf
except ImportError:
    warn = "The jellyfish library was not found. Some distance matrices will be unavailable."
    Warning(warn)


class DistMatrix:
    """
    Generalized class for creating distance matrices from lists of aligned 
    protein or DNA sequences using arbitrary distance functions.
    """

    def __init__(self,alphabet="amino",internal_type=int):
        """
        Initialize the class.  This should be called by every subclass to
        initialize the internal dictionaries mapping alphabets to fast internal
        indexes. 
        """

        # initialize internal variables
        self.alphabet = alphabet
        self.internal_type = internal_type
        self.data_vector = None
        self.dist_matrix = None

        # decide on the alphabet
        if self.alphabet == "amino": 
            self._alphabet_string = 'ACDEFGHIKLMNPQRSTVWY*BZX'
        elif self.alphabet == "dna":
            self._alphabet_string = 'ACGT*'
        else:
            raise ValueError("alphabet not recongized.")

        # create a dictionary mapping the alphabet to a fast internal index
        # (usually an int)
        enum_list = zip(self._alphabet_string,range(len(self._alphabet_string)))
        if self.internal_type == int:
            self._alphabet_dict = dict([(a, i) for a, i in enum_list])
        elif self.internal_type == float:
            self._alphabet_dict = dict([(a, 1.0*i) for a, i in enum_list])
        elif self.internal_type == str:
            self._alphabet_dict = dict([(a, a) for a, i in enum_list])
        else:
            raise ValueError("unrecognized internal type.")

    def create_data_vector(self,phage_file,k_cutoff=1.00):
        """
        Create an array of numpy arrays holding individual sequences that
        should be compared to one another. 

        Currently just reads in the human-readable-summary.txt output from 
        the regression and takes all sequences with k > k_cutoff.
        """

        self.data_vector = []
        self.seq_strings = []
        with open(phage_file) as data:

            next(data)
            for line in data:
                num, seq, k_glob, theta_glob, k_ind, theta_ind = line.split()
                if float(k_ind) > k_cutoff:

                    self.seq_strings.append(seq)

                    self.data_vector.append(
                        np.array([self._alphabet_dict[s] for s in seq],
                                 dtype=self.internal_type))
    
        self.data_vector = np.array(self.data_vector)

    def calc_dist_matrix(self):
        """
        Calculate all pairwise distances between the sequences in 
        self.data_vector, creating the self.dist_matrix in the process. 
        """

        nrow = self._data_vector.shape[0]
        self.dist_matrix = np.zeros((nrow, nrow),dtype=float)
        for i in range(nrow):
            for j in range(i + 1, nrow):
                self.dist_matrix[i,j] = self._pairwise(self._data_vector[i],self._data_vector[j])
                self.dist_matrix[j,i] = self.dist_matrix[i,j]
     
        self.dist_frame = pd.DataFrame(self.dist_matrix,
                                       index = self.seq_strings,
                                       columns = self.seq_strings)

    def _pairwise(self,s1,s2):
        """
        Pairwise distance function.  This should be defined for the various
        daughter classes.
        """

        return 0.0

    def plot_hist(self):
        """
        Make histogram plot of frequency of sequence distance scores in the
        given distance matrix.  Use the dist_frame pandas data frame to use 
        pandas plotting methods.
        """
        
        plt.figure();
        self.dist_frame.plot(kind='hist',legend=False,orientation='horizontal')


class HammingDistMatrix(DistMatrix):
    """
    Create a matrix using a Hamming distance.  This actually just wraps the 
    scipy hamming distance matrix calculator, ignoring self._pairwise.  
    """

    def __init__(self,alphabet="amino"):
        """
        Standard init function.
        """

        super(self.__class__,self).__init__(alphabet,int)

    def calc_dist_matrix(self):
        """
        Use the built-in scipy hamming distance calculator for this.
        """

        self.dist_matrix = spatial.distance.squareform(spatial.distance.pdist(self._data_vector,metric="hamming")))

    
class WeightedDistMatrix(DistMatrix):
    """
    Calculate a weighted distance matrix.  This defaults to Blosum62, but can 
    calculate any distance that has the form 1 - d1*d2*d3*...dn .
    """

    def __init__(self,matrix_file="weight_matrices/blosum62.txt",alphabet="amino"):
        """
        Standard init function, but add creation of a weight matrix from 
        input file (blosum62.txt by default). 
        """

        # Call the base class __init__ function.
        super(self.__class__,self).__init__(alphabet,int)

        # Read in the matrix file    
        self._weight_file = matrix_file
        self._read_weight_file()

    def _read_weight_file(self):
        """
        Read a weight/distance matrix file into a numpy array.  
        """

        data = open(self._weight_file).readlines()

        # Grab alphabet bits from top line
        seq = [self._alphabet_dict[s] for s in data[0].strip('/n/r').split()]
       
        # Go through each line, populating weight matrix. 
        self.weight_matrix = np.zeros((len(seq),len(seq)),dtype=float)
        for line in data[1:]:
            line = line.strip('/n/r').split()

            a = self._alphabet_dict[line[0]]
            for j in range(1, len(line)):
                b = seq[j-1]
                self.weight_matrix[a, b] = exp(float(line[j]))

    def _pairwise_dist(self,seq1,seq2):

        return 1 - np.prod(self._matrix[seq1,seq2])

class DamerauDistMatrix:
    """
    Calculate a Damerau/Levenshtein distance between strings.  Requires jellyfish.
    """

    def __init__(self,alphabet):
        """
        Standard init function.  Only peculiarity is that this class stores the 
        sequences internally as strings.
        """

        super(self.__class__,self).__init__(alphabet,str)

    def _pairwise_dist(self,seq1,seq2):
        """
        For pairwise distance, use jellyfish implementation.
        """
    
        return jf.damerau_levenshtein_distance(str(seq1), str(seq2))
