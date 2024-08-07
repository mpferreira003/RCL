import numpy as np
import tensorflow as tf
from transformers import BertTokenizer, TFBertForSequenceClassification
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt

class BertPredictor():
  def __init__(self,num_labels,verbose=True):
    # Carregar o tokenizador e o modelo pré-treinado BERT
    self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    self.model = TFBertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=num_labels)
    self.verbose = verbose
  def compile(self,
                  optimizer=tf.keras.optimizers.legacy.Adam(learning_rate=3e-5),
                  loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                  metrics=[tf.keras.metrics.SparseCategoricalAccuracy()]):
    self.model.compile(optimizer=optimizer, loss=loss, metrics=metrics)
    if self.verbose:self.model.summary()
  def __preprocess__(self,texts,labels=None,max_length=128):
    input_ids = []
    attention_masks = []
    for text in texts:
        encoded_dict = self.tokenizer.encode_plus(
                            text,
                            add_special_tokens = True,
                            max_length = max_length,
                            pad_to_max_length = True,
                            return_attention_mask = True,
                            return_tensors = 'tf',
                       )
        input_ids.append(encoded_dict['input_ids'])
        attention_masks.append(encoded_dict['attention_mask'])

    input_ids = tf.concat(input_ids, axis=0)
    attention_masks = tf.concat(attention_masks, axis=0)

    if labels is not None:
      labels = tf.convert_to_tensor(labels)
      return input_ids, attention_masks, labels
    return input_ids,attention_masks

  def fit(self,X,Y,
          epochs=10,
          batch_size=8,
          callbacks = [
              tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=3),
              tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=2)
          ],
          validation_data = None# colocar como [X,Y]
          ):

    train_input_ids,train_attention_masks,train_labels = self.__preprocess__(X,Y)

    if validation_data is not None:
      run_with_validation = True
      test_input_ids, test_attention_masks,test_labels = self.__preprocess__(validation_data[0],validation_data[1])
    else:
      run_with_validation = False

    class_weights = compute_class_weight('balanced', classes=np.unique(train_labels), y=train_labels.numpy())
    self.class_weights_dict = dict(enumerate(class_weights))

    self.history = self.model.fit(
        [train_input_ids, train_attention_masks],
        train_labels,
        validation_data= None if not run_with_validation else ([test_input_ids, test_attention_masks], test_labels),
        epochs=epochs,  # Número de épocas
        batch_size=batch_size,  # Tamanho do lote
        callbacks=callbacks,
        class_weight=self.class_weights_dict
    )
    return self.history

  @staticmethod
  def plot_history(history):
    for key in history.history.keys():
      plt.plot(history.history[key], label=key)
    plt.legend()
    plt.show()

  def predict(self,X):
    input_ids, attention_masks = self.__preprocess__(X)
    predictions = self.model.predict([input_ids, attention_masks])
    predicted_labels = np.argmax(predictions.logits, axis=1)
    return predicted_labels
