# FAIRS-forecasting

## Project description
This script has been developed to allow roulette timeseries forecasting using a series of custom Recurrent Neural Network (RNN) models. Different approaches have been envisaged to accurately predict the probability of a number being the next extraction, by relying on both single number or categorical classification (black, red and green). THe rationale behind the different models is to use Long Short-Term Memory (LSTM) together with Embedding functionality for processing sequential data, having as output the probability distribution over possible next numbers. The input sequence is transformed into a dense vectors of fixed size, before being processed recursively by a series of LSTM layers with increasing neurons number. Once the temporal dependencies from the input sequence are learned by the model, a series of Dense layers map the extracted features to the output space. The final Dense layer is provided with softmax activation in order to output a probability distribution over possible next numbers. Overfitting is largely prevented by using Dropout layers in between.

## How to use
Run the FAIRS.py file to launch the script and use the main menu to navigate the different options. The main menu will provide the user with the following options:
**1) FAIRS timeseries analysis:** Perform timeseries analysis to visualize distribution and main statistical parameters                
**2) FAIRS training: Color Code Model (CCM)** Open sub-menu for CC model pretraining                                   
**3) Exit and close**

The Color Code Model (CCM) sub-menu will provide the following options:

**1) Pretrain ColorCode model:**
**2) Evaluate ColorCode model:**
**3) Predict next extraction:**
**4) Go back to main menu**

### Requirements
This application has been developed and tested using the following dependencies (Python 3.10.12):

- `keras==2.10.0`
- `matplotlib==3.7.2`
- `numpy==1.25.2`
- `pandas==2.0.3`
- `scikit-learn==1.3.0`
- `seaborn==0.12.2`
- `tensorflow==2.10.0`
- `xlrd==2.0.1`
- `XlsxWriter==3.1.3`
- `pydot==1.4.2`
- `graphviz==0.20.1`

These dependencies are specified in the provided `requirements.txt` file to ensure full compatibility with the application. 
