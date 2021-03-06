from tabnanny import verbose
from absl import app, flags, logging
from absl.flags import FLAGS
from glob import glob
import cv2
import os
import numpy as np
import tensorflow as tf
from tqdm import tqdm

from modules.evaluations import get_val_data, perform_val
from modules.models import ArcFaceModel
from modules.utils import set_memory_growth, load_yaml, l2_norm


flags.DEFINE_string('cfg_path', './configs/arc_res50.yaml', 'config file path')
flags.DEFINE_string('gpu', '0', 'which gpu to use')
flags.DEFINE_string('img_path', '', 'path to input image')
flags.DEFINE_string('head_type', 'all', 'whether to use all heads or specific ones')


def main(_argv):
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    os.environ['CUDA_VISIBLE_DEVICES'] = FLAGS.gpu

    logger = tf.get_logger()
    logger.disabled = True
    logger.setLevel(logging.FATAL)
    set_memory_growth()

    cfg = load_yaml(FLAGS.cfg_path)

    model = ArcFaceModel(size=cfg['input_size'],
                         backbone_type=cfg['backbone_type'],
                         training=False)


    ckpt_path = tf.train.latest_checkpoint('./checkpoints/' + cfg['sub_name'])
    if ckpt_path is not None:
        print("[*] load ckpt from {}".format(ckpt_path))
        model.load_weights(ckpt_path)
    else:
        print("[*] Cannot find ckpt from {}.".format(ckpt_path))
        exit()

    if FLAGS.img_path:
        imgs = glob(f"{FLAGS.img_path}/**/*.*", recursive=True)
        predictions = []    
        for img_fn in tqdm(imgs, total=len(list(imgs))):
            img = cv2.imread(img_fn)
            img = cv2.resize(img, (224, 224))
            img = img.astype(np.float32) / 255.
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            if len(img.shape) == 3:
                img = np.expand_dims(img, 0)
            if FLAGS.head_type == "classif":
                pred_string = f"{np.argmax(model(img))},{img_fn}"
            elif FLAGS.head_type == "all":
                pred_string = f"{np.argmax(model([img, [np.zeros(cfg['num_classes'])]]))},{img_fn}"
            predictions.append(pred_string)
            
        results_file = open("results.csv", 'w')
        results_file.write('\n'.join(predictions))
        results_file.close()
    else:
        print("[*] Loading LFW, AgeDB30 and CFP-FP...")
        lfw, agedb_30, cfp_fp, lfw_issame, agedb_30_issame, cfp_fp_issame = \
            get_val_data(cfg['test_dataset'])

        print("[*] Perform Evaluation on LFW...")
        acc_lfw, best_th = perform_val(
            cfg['embd_shape'], cfg['batch_size'], model, lfw, lfw_issame,
            is_ccrop=cfg['is_ccrop'])
        print("    acc {:.4f}, th: {:.2f}".format(acc_lfw, best_th))

        # print("[*] Perform Evaluation on AgeDB30...")
        # acc_agedb30, best_th = perform_val(
        #     cfg['embd_shape'], cfg['batch_size'], model, agedb_30,
        #     agedb_30_issame, is_ccrop=cfg['is_ccrop'])
        # print("    acc {:.4f}, th: {:.2f}".format(acc_agedb30, best_th))

        # print("[*] Perform Evaluation on CFP-FP...")
        # acc_cfp_fp, best_th = perform_val(
        #     cfg['embd_shape'], cfg['batch_size'], model, cfp_fp, cfp_fp_issame,
        #     is_ccrop=cfg['is_ccrop'])
        # print("    acc {:.4f}, th: {:.2f}".format(acc_cfp_fp, best_th))


if __name__ == '__main__':
    try:
        app.run(main)
    except SystemExit:
        pass
