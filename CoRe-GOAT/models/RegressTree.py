# modify due to 228 pytorch version.
# module 'torch' has no attribute 'log_softmax'
# use F.log_softmax instead

import mindspore.nn as nn
import mindspore.ops as ops
        
class RegressTree(nn.Cell):
    def __init__(self, in_channel, hidden_channel, depth):
        super(RegressTree, self).__init__()
        self.depth = depth
        self.num_leaf = 2 ** (depth - 1)

        self.first_layer = nn.SequentialCell([
            nn.Dense(in_channel, hidden_channel),
            nn.ReLU()
        ])

        self.feature_layers = nn.CellList([self.get_tree_layer(2**d, hidden_channel) for d in range(self.depth - 1)])
        self.clf_layers = nn.CellList([self.get_clf_layer(2**d, hidden_channel) for d in range(self.depth - 1)])
        self.reg_layer = nn.Conv1d(self.num_leaf * hidden_channel, self.num_leaf, 1, group=self.num_leaf)
    @staticmethod
    def get_tree_layer(num_node_in, hidden_channel=256):
        return nn.SequentialCell([
            nn.Conv1d(num_node_in * hidden_channel, num_node_in * 2 * hidden_channel, 1, group=num_node_in),
            nn.ReLU()
        ])

    @staticmethod
    def get_clf_layer(num_node_in, hidden_channel=256):
        return nn.Conv1d(num_node_in * hidden_channel, num_node_in * 2, 1, group=num_node_in)

    def construct(self, input_feature):
        out_prob = []
        x = self.first_layer(input_feature)
        bs = x.shape[0]
        x = x.unsqueeze(-1)
        for i in range(self.depth - 1):
            prob = self.clf_layers[i](x).squeeze(-1)
            x = self.feature_layers[i](x)
            # print(prob.shape,x.shape)d
            if len(out_prob) > 0:
                prob = ops.log_softmax(prob.view(bs, -1, 2), axis=-1)
                pre_prob = out_prob[-1].view(bs, -1, 1).broadcast_to((bs, -1, 2))
                prob = pre_prob + prob
                out_prob.append(prob)
            else:
                out_prob.append(ops.log_softmax(prob.view(bs, -1, 2), axis=-1))  # 2 branch only
        delta = self.reg_layer(x).squeeze(-1)
        # leaf_prob = torch.exp(out_prob[-1].view(bs, -1))
        # assert delta.size() == leaf_prob.size()
        # final_delta = torch.sum(leaf_prob * delta, dim=1)
        return out_prob, delta
      