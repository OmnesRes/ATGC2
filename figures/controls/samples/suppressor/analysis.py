import numpy as np
import tensorflow as tf
from model.Sample_MIL import InstanceModels, RaggedModels
from model.KerasLayers import Losses, Metrics
from model import DatasetsUtils
from sklearn.model_selection import StratifiedShuffleSplit, StratifiedKFold
from sklearn.metrics import classification_report
import pickle
physical_devices = tf.config.experimental.list_physical_devices('GPU')
tf.config.experimental.set_memory_growth(physical_devices[-1], True)
tf.config.experimental.set_visible_devices(physical_devices[-1], 'GPU')

import pathlib
path = pathlib.Path.cwd()
if path.stem == 'ATGC':
    cwd = path
else:
    cwd = list(path.parents)[::-1][path.parts.index('ATGC')]
    import sys
    sys.path.append(str(cwd))


D, maf = pickle.load(open(cwd / 'figures' / 'controls' / 'data' / 'data.pkl', 'rb'))
sample_df = pickle.load(open('files/tcga_sample_table.pkl', 'rb'))

strand_emb_mat = np.concatenate([np.zeros(2)[np.newaxis, :], np.diag(np.ones(2))], axis=0)
D['strand_emb'] = strand_emb_mat[D['strand']]

frame_emb_mat = np.concatenate([np.zeros(3)[np.newaxis, :], np.diag(np.ones(3))], axis=0)
D['cds_emb'] = frame_emb_mat[D['cds']]


pos_bins = [100, 100]
bin_sizes = []
D['cum_pos'] = D['cum_pos'] - min(D['cum_pos'])
max_pos = max(D['cum_pos'])
for bin in pos_bins:
    size = np.ceil(max_pos / bin)
    bin_sizes.append(size)
    max_pos = size

##bin positions according to chosen bins
def pos_one_hot(cum_pos, bin_sizes=bin_sizes):
    bins = []
    pos = cum_pos
    for size in bin_sizes:
        bin = int(pos / size)
        bins.append(bin)
        pos = pos - bin * size

    return bins, pos / size

result = np.apply_along_axis(pos_one_hot, -1, D['cum_pos'][:, np.newaxis])

D['pos_bin'] = np.stack(np.array(result[:, 0])) + 1
D['pos_loc'] = np.stack(result[:, 1])

bin_0 = D['pos_bin'][:, 0]
bin_1 = D['pos_bin'][:, 1]

indexes = [np.where(D['sample_idx'] == idx) for idx in range(sample_df.shape[0])]

pos_loc = np.array([D['pos_loc'][i] for i in indexes], dtype='object')
bin_0 = np.array([bin_0[i] for i in indexes], dtype='object')
bin_1 = np.array([bin_1[i] for i in indexes], dtype='object')

# set y label and weights
genes = maf['Hugo_Symbol'].values
boolean = ['PTEN' in genes[j] for j in [np.where(D['sample_idx'] == i)[0] for i in range(sample_df.shape[0])]]
y_label = np.stack([[0, 1] if i else [1, 0] for i in boolean])
y_strat = np.argmax(y_label, axis=-1)

# y_strat = np.ones(y_label.shape[0])
class_counts = dict(zip(*np.unique(y_strat, return_counts=True)))
y_weights = np.array([1 / class_counts[_] for _ in y_strat])
y_weights /= np.sum(y_weights)

pos_loader = DatasetsUtils.Map.FromNumpy(pos_loc, tf.float32)
bin_0_loader = DatasetsUtils.Map.FromNumpy(bin_0, tf.int32)
bin_1_loader = DatasetsUtils.Map.FromNumpy(bin_1, tf.int32)


with open('figures/controls/samples/suppressor/results/weights.pkl', 'rb') as f:
    weights = pickle.load(f)

position_encoder = InstanceModels.VariantPositionBin(bins=pos_bins, fusion_dimension=128)
mil = RaggedModels.MIL(instance_encoders=[position_encoder.model], output_dims=[2], pooling='sum', mil_hidden=(64, 32, 16, 8), output_types=['anlulogits'])

test_idx = []
predictions = []
attentions = []
instance_labels = []
for index, (idx_train, idx_test) in enumerate(StratifiedKFold(n_splits=8, random_state=0, shuffle=True).split(y_strat, y_strat)):
    mil.model.set_weights(weights[index])

    ds_test = tf.data.Dataset.from_tensor_slices((idx_test, y_label[idx_test]))
    ds_test = ds_test.batch(len(idx_test), drop_remainder=False)
    ds_test = ds_test.map(lambda x, y: ((bin_0_loader(x, ragged_output=True),
                                           bin_1_loader(x, ragged_output=True),
                                           pos_loader(x, ragged_output=True),
                                           ),
                                           y,
                                           ))

    predictions.append(mil.model.predict(ds_test))
    test_idx.append(idx_test)
    attentions.append(mil.attention_model.predict(ds_test).to_list())
    instance_labels.append(genes[np.concatenate(np.array(indexes, dtype=object)[idx_test].tolist(), axis=1)[0]] == 'PTEN')

with open('figures/controls/samples/suppressor/results/predictions.pkl', 'wb') as f:
    pickle.dump([y_strat, test_idx, predictions], f)

with open('figures/controls/samples/suppressor/results/latent.pkl', 'wb') as f:
    pickle.dump([attentions, instance_labels], f)

print(classification_report(y_strat[np.concatenate(test_idx, axis=-1)], np.argmax(np.concatenate(predictions, axis=0), axis=-1), digits=4))

#
# #
# test=maf.iloc[np.concatenate(np.array([np.where(D['sample_idx'] == i)[0] for i in range(y_label.shape[0])])[test_idx[0]], axis=-1)]['Hugo_Symbol'][np.concatenate(attentions[0]).flat > .5]
#
# sorted(list(zip(np.concatenate(attentions[0]).flat[np.concatenate(attentions[0]).flat > .5],
#                 test,
#                 D['pos_bin'][np.concatenate(np.array([np.where(D['sample_idx'] == i)[0] for i in range(y_label.shape[0])])[test_idx[0]], axis=-1)][np.concatenate(attentions[0]).flat > .5],
#                 D['pos_loc'][:,0][np.concatenate(np.array([np.where(D['sample_idx'] == i)[0] for i in range(y_label.shape[0])])[test_idx[0]], axis=-1)][np.concatenate(attentions[0]).flat> .5])))




