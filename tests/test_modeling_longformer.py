# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unittest

import torch

from transformers import is_torch_available

from .test_configuration_common import ConfigTester
from .test_modeling_common import ModelTesterMixin, ids_tensor
from .utils import require_torch, slow, torch_device


if is_torch_available():
    from transformers import (
        LongformerConfig,
        LongformerModel,
        LongformerForMaskedLM,
    )
    from transformers.modeling_longformer import LONGFORMER_PRETRAINED_MODEL_ARCHIVE_MAP


@require_torch
class LongformerModelTest(ModelTesterMixin, unittest.TestCase):
    test_pruning = False  # pruning is not supported
    test_headmasking = False  # head masking is not supported
    test_torchscript = False

    all_model_classes = (LongformerForMaskedLM, LongformerModel) if is_torch_available() else ()

    class LongformerModelTester(object):
        def __init__(
            self,
            parent,
            batch_size=13,
            seq_length=8,
            is_training=True,
            use_input_mask=True,
            use_token_type_ids=True,
            use_labels=True,
            vocab_size=99,
            hidden_size=32,
            num_hidden_layers=5,
            num_attention_heads=4,
            intermediate_size=37,
            hidden_act="gelu",
            hidden_dropout_prob=0.1,
            attention_probs_dropout_prob=0.1,
            max_position_embeddings=512,
            type_vocab_size=16,
            type_sequence_label_size=2,
            initializer_range=0.02,
            num_labels=3,
            num_choices=4,
            scope=None,
            attention_window=4,
        ):
            self.parent = parent
            self.batch_size = batch_size
            self.seq_length = seq_length
            self.is_training = is_training
            self.use_input_mask = use_input_mask
            self.use_token_type_ids = use_token_type_ids
            self.use_labels = use_labels
            self.vocab_size = vocab_size
            self.hidden_size = hidden_size
            self.num_hidden_layers = num_hidden_layers
            self.num_attention_heads = num_attention_heads
            self.intermediate_size = intermediate_size
            self.hidden_act = hidden_act
            self.hidden_dropout_prob = hidden_dropout_prob
            self.attention_probs_dropout_prob = attention_probs_dropout_prob
            self.max_position_embeddings = max_position_embeddings
            self.type_vocab_size = type_vocab_size
            self.type_sequence_label_size = type_sequence_label_size
            self.initializer_range = initializer_range
            self.num_labels = num_labels
            self.num_choices = num_choices
            self.scope = scope
            self.attention_window = attention_window

            # `ModelTesterMixin.test_attention_outputs` is expecting attention tensors to be of size
            # [num_attention_heads, encoder_seq_length, encoder_key_length], but LongformerSelfAttention
            # returns attention of shape [num_attention_heads, encoder_seq_length, self.attention_window + 1]
            # because its local attention only attends to `self.attention_window + 1` locations
            self.key_length = self.attention_window + 1

        def prepare_config_and_inputs(self):
            input_ids = ids_tensor([self.batch_size, self.seq_length], self.vocab_size)

            input_mask = None
            if self.use_input_mask:
                input_mask = ids_tensor([self.batch_size, self.seq_length], vocab_size=2)

            token_type_ids = None
            if self.use_token_type_ids:
                token_type_ids = ids_tensor([self.batch_size, self.seq_length], self.type_vocab_size)

            sequence_labels = None
            token_labels = None
            choice_labels = None
            if self.use_labels:
                sequence_labels = ids_tensor([self.batch_size], self.type_sequence_label_size)
                token_labels = ids_tensor([self.batch_size, self.seq_length], self.num_labels)
                choice_labels = ids_tensor([self.batch_size], self.num_choices)

            config = LongformerConfig(
                vocab_size=self.vocab_size,
                hidden_size=self.hidden_size,
                num_hidden_layers=self.num_hidden_layers,
                num_attention_heads=self.num_attention_heads,
                intermediate_size=self.intermediate_size,
                hidden_act=self.hidden_act,
                hidden_dropout_prob=self.hidden_dropout_prob,
                attention_probs_dropout_prob=self.attention_probs_dropout_prob,
                max_position_embeddings=self.max_position_embeddings,
                type_vocab_size=self.type_vocab_size,
                initializer_range=self.initializer_range,
                attention_window=self.attention_window,
            )

            return config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels

        def check_loss_output(self, result):
            self.parent.assertListEqual(list(result["loss"].size()), [])

        def create_and_check_longformer_model(
            self, config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels
        ):
            model = LongformerModel(config=config)
            model.to(torch_device)
            model.eval()
            sequence_output, pooled_output = model(input_ids, attention_mask=input_mask, token_type_ids=token_type_ids)
            sequence_output, pooled_output = model(input_ids, token_type_ids=token_type_ids)
            sequence_output, pooled_output = model(input_ids)

            result = {
                "sequence_output": sequence_output,
                "pooled_output": pooled_output,
            }
            self.parent.assertListEqual(
                list(result["sequence_output"].size()), [self.batch_size, self.seq_length, self.hidden_size]
            )
            self.parent.assertListEqual(list(result["pooled_output"].size()), [self.batch_size, self.hidden_size])

        def create_and_check_longformer_for_masked_lm(
            self, config, input_ids, token_type_ids, input_mask, sequence_labels, token_labels, choice_labels
        ):
            model = LongformerForMaskedLM(config=config)
            model.to(torch_device)
            model.eval()
            loss, prediction_scores = model(
                input_ids, attention_mask=input_mask, token_type_ids=token_type_ids, masked_lm_labels=token_labels
            )
            result = {
                "loss": loss,
                "prediction_scores": prediction_scores,
            }
            self.parent.assertListEqual(
                list(result["prediction_scores"].size()), [self.batch_size, self.seq_length, self.vocab_size]
            )
            self.check_loss_output(result)

        def prepare_config_and_inputs_for_common(self):
            config_and_inputs = self.prepare_config_and_inputs()
            (
                config,
                input_ids,
                token_type_ids,
                input_mask,
                sequence_labels,
                token_labels,
                choice_labels,
            ) = config_and_inputs
            inputs_dict = {"input_ids": input_ids, "token_type_ids": token_type_ids, "attention_mask": input_mask}
            return config, inputs_dict

    def setUp(self):
        self.model_tester = LongformerModelTest.LongformerModelTester(self)
        self.config_tester = ConfigTester(self, config_class=LongformerConfig, hidden_size=37)

    def test_config(self):
        self.config_tester.run_common_tests()

    def test_longformer_model(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_longformer_model(*config_and_inputs)

    def test_longformer_for_masked_lm(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_longformer_for_masked_lm(*config_and_inputs)

    @slow
    def test_model_from_pretrained(self):
        for model_name in list(LONGFORMER_PRETRAINED_MODEL_ARCHIVE_MAP.keys())[:1]:
            model = LongformerModel.from_pretrained(model_name)
            self.assertIsNotNone(model)


class LongformerModelIntegrationTest(unittest.TestCase):
    @slow
    def test_inference_no_head(self):
        model = LongformerModel.from_pretrained("longformer-base-4096")
        input_ids = torch.tensor([[0] + [20920, 232, 328, 1437] * 1000 + [2]])  # long input
        output = model(input_ids)[0]
        expected_output_sum = torch.tensor(74518.2344)
        expected_output_mean = torch.tensor(0.0242)

        self.assertTrue(torch.allclose(output.sum(), expected_output_sum, atol=1e-4))
        self.assertTrue(torch.allclose(output.mean(), expected_output_mean, atol=1e-4))

    @slow
    def test_inference_masked_lm(self):
        model = LongformerForMaskedLM.from_pretrained("longformer-base-4096")
        input_ids = torch.tensor([[0] + [20920, 232, 328, 1437] * 1000 + [2]])  # long input

        loss, prediction_scores = model(input_ids, masked_lm_labels=input_ids)

        expected_loss = torch.tensor(0.0620)
        expected_prediction_scores_sum = torch.tensor(-6.1599e08)
        expected_prediction_scores_mean = torch.tensor(-3.0622)

        self.assertTrue(torch.allclose(loss, expected_loss, atol=1e-4))
        self.assertTrue(torch.allclose(prediction_scores.sum(), expected_prediction_scores_sum, atol=1e-4))
        self.assertTrue(torch.allclose(prediction_scores.mean(), expected_prediction_scores_mean, atol=1e-4))