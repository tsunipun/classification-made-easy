import gradio as gr
import sys
import time
from train_tester import TrainTest

log_refresh_time = 1.0

archs_list = ['vit']
module = TrainTest(arch_name=archs_list[0])

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.message_queue = []
        self.filename = filename
        self.last_log_write_time = time.time()

    def write(self, message):
        self.terminal.write(message)
        while(len(self.message_queue) > 10):
            self.message_queue.pop(0)
        if len(message) > 0:
            self.message_queue.append(message)
        
        if time.time() - self.last_log_write_time > log_refresh_time or message == 'end log!':
            with open(self.filename, "w+") as f:
                f.write(''.join(self.message_queue))
            self.last_log_write_time = time.time()
        
    def flush(self):
        self.terminal.flush()
        
    def isatty(self):
        return False    

sys.stdout = Logger("output.log")

def run_train(data_path):
    # train.main(data_path)
    module.train(data_path)
    print('end log!')
    
def run_test(image):
    # result = test_image.main(image)
    result = module.test(image)
    print('end log!')
    return result

def read_logs():
    sys.stdout.flush()
    with open("output.log", "r") as f:
        return f.read()
    
def reload_module(arch_name):
    global module
    module = TrainTest(arch_name)

with gr.Blocks() as demo:
    with gr.Tab('Train'):
        architecture = gr.Dropdown(choices=archs_list, label='Architecture', value=archs_list[0])
        dataset_path = gr.Text(label='dataset path')
        btn = gr.Button("Train", variant='primary')
        btn.click(run_train, inputs=[dataset_path], outputs=None)
        architecture.change(fn=reload_module, inputs=[architecture], outputs=[])
    with gr.Tab('Test'):
        with gr.Row():
            with gr.Column():
                input_image = gr.Image(label='input', type='pil')
            with gr.Column():        
                btn_test = gr.Button("Test", variant='primary')
                result = gr.Text(label='result')
        btn_test.click(run_test, inputs=[input_image], outputs=[result])
    
    logs = gr.Textbox(label='log')
    logs.attach_load_event(read_logs, every=log_refresh_time)
    # demo.load(read_logs, None, logs)
    
demo.launch(server_name='0.0.0.0', server_port=9800)