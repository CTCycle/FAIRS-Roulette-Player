import os
import pandas as pd
import numpy as np
from keras.utils import set_random_seed
from keras import Model

from FAIRS.app.utils.data.process import RouletteSeriesEncoder
from FAIRS.app.constants import INFERENCE_PATH
from FAIRS.app.logger import logger


###############################################################################
class RoulettePlayer:
    def __init__(self, model : Model, configuration : dict):
        set_random_seed(configuration.get('seed', 42))
        self.model = model
        self.configuration = configuration
        self.perceptive_size = configuration.get('perceptive_field_size', 64)  
        
        self.action_descriptions = {i: f"Bet on number {i}" for i in range(37)}
        self.action_descriptions[37] = "Bet on red"
        self.action_descriptions[38] = "Bet on black"
        self.action_descriptions[39] = "stop playing"

        self.last_states = None
        self.mapper = RouletteSeriesEncoder(configuration)

    # ----------------------------------------------------------------------
    def get_perceptive_fields(self, data: np.ndarray):
        perceptive_field = np.full(shape=self.perceptive_size, fill_value=-1, dtype=np.int32)
        perceptive_fields = [perceptive_field]

        if data.shape[0] > 0:
            extractions = data[:, 0]
            for r in range(data.shape[0]):
                current_extraction = extractions[r]
                perceptive_field = np.delete(perceptive_field, 0)
                perceptive_field = np.append(perceptive_field, current_extraction)
                perceptive_fields.append(perceptive_field)

            total_windows = len(perceptive_fields)
            perceptive_fields_collection = perceptive_fields[-total_windows:]
            self.last_states = perceptive_fields[-1]
        else:
            perceptive_fields_collection = perceptive_fields

        return perceptive_fields_collection

    # ----------------------------------------------------------------------
    def init_state_if_needed(self):
        if self.last_states is None:
            self.last_states = np.full(
                shape=self.perceptive_size, fill_value=-1, dtype=np.int32)

    # ----------------------------------------------------------------------
    def predict_next(self):        
        self.init_state_if_needed()
        current_state = self.last_states.reshape(1, self.perceptive_size)
        # verbose=0 to keep the process quiet; GUI shows results
        action_logits = self.model.predict(current_state, verbose=0)
        next_action = int(np.argmax(action_logits, axis=1)[0])
        return {
            "action": next_action,
            "description": self.action_descriptions.get(next_action, f"action {next_action}")}

    # ----------------------------------------------------------------------
    def apply_true(self, real_number: int):       
        if not isinstance(real_number, (int, np.integer)):
            raise ValueError("Real extraction must be an integer.")
        if real_number < 0 or real_number > 36:
            raise ValueError("Real extraction must be in [0, 36].")

        self.init_state_if_needed()
        # roll window and append the new value
        self.last_states = np.append(self.last_states[1:], np.int32(real_number))