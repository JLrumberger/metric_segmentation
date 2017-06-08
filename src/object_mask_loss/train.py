import numpy as np
import tensorflow as tf
import os

from model import create_UNet
from object_mask_loss.loss import object_mask_loss
from provider import EMDataGenerator

def train(params):
  """Trains and monitors net"""
  data_dir = params['data_dir']
  log_dir = params['log_dir']
  model_dir = params['model_dir']
  save_dir = params['save_dir']
  K = params['n_sampled_objects']
  alpha = params['alpha']

  # Create input, output placeholders
  em_input, vec_labels = create_UNet(params)
  mask_list_input = [tf.placeholder(dtype=tf.float32, shape=(1,params['out_height'], params['out_width'], 1))]*K

  # Create loss
  loss = object_mask_loss(vec_labels, mask_list_input, alpha)

  # Create train op
  optimizer = tf.train.AdamOptimizer(learning_rate=0.001)#, momentum=0.9)
  train_op = optimizer.minimize(loss)

  # Initialize data provider
  em_train = EMDataGenerator(data_dir, 'train')
  em_dev = EMDataGenerator(data_dir, 'dev')

  # Initialize session
  init_op = tf.global_variables_initializer()
  sess = tf.Session()
  sess.run(init_op)

  # Create logging utils
  writer = tf.summary.FileWriter(log_dir, graph=tf.get_default_graph())
  train_loss_summary = tf.summary.scalar("train_loss", loss)
  valid_loss_summary = tf.summary.scalar("val_loss", loss)
  #summary_op = tf.summary.merge_all()

  saver = tf.train.Saver(max_to_keep=100)

  # Train
  max_steps = 100000
  print("-------------Training-----------------")
  for i in range(max_steps):
    # Get Data
    em_input_data_train, mask_list_data_train = em_train.next_batch(1)
    em_input_data_dev, mask_list_data_dev = em_dev.next_batch(1)

    # Infer + Backprop
    feed_dict = {em_input: em_input_data_train,
                  mask_list_input: mask_list_data_train}
    _, train_summary = sess.run([train_op, train_loss_summary], feed_dict=feed_dict)

    if i % 2 == 0:
      feed_dict = {em_input: em_input_data_dev,
                  mask_list_input: mask_list_data_dev}
      valid_summary = sess.run(valid_loss_summary, feed_dict=feed_dict)

      # Monitor progress
      writer.add_summary(train_summary, i)
      writer.add_summary(valid_summary, i)

    # Checkpoint periodically
    if i % 2000 == 0:
      print("Processed {} epochs.".format(i))
      # Save model
      saver.save(sess, os.path.join(model_dir, "model{}.ckpt".format(i)))

      # Save some sample images-train
      feed_dict = {em_input: em_input_data_train,
                    mask_list_input: mask_list_data_train}

      vec_label_data = sess.run(vec_labels, feed_dict=feed_dict)
      np.save(os.path.join(save_dir, 'vec_labels{}'.format(i)), vec_label_data)
      np.save(os.path.join(save_dir, 'human_labels{}'.format(i)), human_label_data_train)
      np.save(os.path.join(save_dir, 'em_img{}'.format(i)), em_input_data_train)

      # Save some sample images-valid
      feed_dict = {em_input: em_input_data_dev,
                mask_list_input: mask_list_data_dev}

      vec_label_data = sess.run(vec_labels, feed_dict=feed_dict)
      np.save(os.path.join(save_dir, 'vec_labels_dev{}'.format(i)), vec_label_data)
      np.save(os.path.join(save_dir, 'human_labels_dev{}'.format(i)), human_label_data_dev)
      np.save(os.path.join(save_dir, 'em_img_dev{}'.format(i)), em_input_data_dev)
