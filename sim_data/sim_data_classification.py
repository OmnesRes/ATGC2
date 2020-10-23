import numpy as np
from sim_data.sim_data_tools import *
import pickle
import pathlib
path = pathlib.Path.cwd()
if path.stem == 'ATGC2':
    cwd = path
else:
    cwd = list(path.parents)[::-1][path.parts.index('ATGC2')]

##this function is designed to have a positive sample defined by 1 or more types of variants.
##option for having negative samples contain a positive variant if positive sample defined by multiple variants

def generate_sample(mean_variants=[50, 100, 300], mean_positive=None, control=True, positive_choices=None, negative_instances=False):
    if negative_instances and len(positive_choices) <= 1:
        raise ValueError
    total_count = int(np.random.normal(np.random.choice(mean_variants, 1), 10))
    if total_count < 1:
        total_count *= -1
    if total_count == 0:
        total_count = 1
    if control:
        if negative_instances:
            positive_count = int(np.ceil(mean_positive * total_count))
            control_count = total_count - positive_count
        else:
            control_count = total_count
            positive_count = 0
    else:
        positive_count = int(np.ceil(mean_positive * total_count))
        control_count = total_count + positive_count * len(positive_choices)

    positive_variants = []
    positive_instances = []

    control_variants = [generate_variant() for i in range(control_count)]
    if control:
        while True:
            y = False
            for i in control_variants:
                if check_variant(i, positive_choices):
                    print('checked')
                    y = True
                    break
            if y:
                control_variants = [generate_variant() for i in range(control_count)]
            else:
                break

    if control:
        if negative_instances:
            positive_choice = int(np.random.choice(range(len(positive_choices)), 1))
            for i in range(positive_count):
                positive_variants.append(positive_choices[positive_choice])
                positive_instances.append(positive_choice + 1)
        else:
            pass

    else:
        for index, i in enumerate(positive_choices):
            for ii in range(positive_count):
                positive_variants.append(i)
                positive_instances.append(index + 1)

    return [control_variants + positive_variants, [0] * len(control_variants) + positive_instances]


##dictionary for instance level data
instances = {'sample_idx': [],
                 'seq_5p': [],
                 'seq_3p': [],
                  'seq_ref': [],
                  'seq_alt': [],
                  'chr': [],
                  'pos_float': [],
                  'strand': [],
                  'cds': [],
                  'class': []}

##how many different variants you want to label a positive sample
positive_choices = [generate_variant() for i in range(1)]

samples = {'classes': []}

for idx in range(500):
    ##what percent of samples are control
    if np.random.sample() < .5:
        variants = generate_sample(negative_instances=False, mean_positive=.02, positive_choices=positive_choices)
        samples['classes'] = samples['classes'] + [0]
    else:
        variants = generate_sample(control=False, mean_positive=.02, positive_choices=positive_choices)
        samples['classes'] = samples['classes'] + [1]
    instances['sample_idx'] = instances['sample_idx'] + [idx] * len(variants[0])
    instances['seq_5p'] = instances['seq_5p'] + [i[0] for i in variants[0]]
    instances['seq_3p'] = instances['seq_3p'] + [i[1] for i in variants[0]]
    instances['seq_ref'] = instances['seq_ref'] + [i[2] for i in variants[0]]
    instances['seq_alt'] = instances['seq_alt'] + [i[3] for i in variants[0]]
    instances['chr'] = instances['chr'] + [i[4] for i in variants[0]]
    instances['pos_float'] = instances['pos_float'] + [i[5] for i in variants[0]]
    instances['strand'] = instances['strand'] + [i[6] for i in variants[0]]
    instances['cds'] = instances['cds'] + [0 for i in variants[0]]
    instances['class'] = instances['class'] + variants[1]

for i in instances:
    instances[i] = np.array(instances[i])

nucleotide_mapping = {'-': 0, 'N': 0, 'A': 1, 'T': 2, 'C': 3, 'G': 4}
instances['seq_5p'] = np.stack(np.apply_along_axis(lambda x: np.array([nucleotide_mapping[i] for i in x]), -1, instances['seq_5p']), axis=0)
instances['seq_3p'] = np.stack(np.apply_along_axis(lambda x: np.array([nucleotide_mapping[i] for i in x]), -1, instances['seq_3p']), axis=0)
instances['seq_ref'] = np.stack(np.apply_along_axis(lambda x: np.array([nucleotide_mapping[i] for i in x]), -1, instances['seq_ref']), axis=0)
instances['seq_alt'] = np.stack(np.apply_along_axis(lambda x: np.array([nucleotide_mapping[i] for i in x]), -1, instances['seq_alt']), axis=0)


variant_encoding = np.array([0, 2, 1, 4, 3])
instances['seq_5p'] = np.stack([instances['seq_5p'], variant_encoding[instances['seq_3p'][:, ::-1]]], axis=2)
instances['seq_3p'] = np.stack([instances['seq_3p'], variant_encoding[instances['seq_5p'][:, :, 0][:, ::-1]]], axis=2)
t = instances['seq_ref'].copy()
i = t != 0
t[i] = variant_encoding[instances['seq_ref'][:, ::-1]][i[:, ::-1]]
instances['seq_ref'] = np.stack([instances['seq_ref'], t], axis=2)
t = instances['seq_alt'].copy()
i = t != 0
t[i] = variant_encoding[instances['seq_alt'][:, ::-1]][i[:, ::-1]]
instances['seq_alt'] = np.stack([instances['seq_alt'], t], axis=2)
del i, t

with open(cwd / 'sim_data' / 'sim_data.pkl', 'wb') as f:
    pickle.dump([instances, samples, ], f)




