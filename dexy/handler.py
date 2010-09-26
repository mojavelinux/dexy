try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from dexy.artifact import Artifact
import dexy.logger
import time

### @export "class"
class DexyHandler(object):
    """
    This is the main DexyHandler class. To make custom handlers you should
    subclass this and override the process() method. You may also want to
    specify INPUT_EXTENSIONS and OUTPUT_EXTENSIONS. You must define unique
    ALIASES in each handler, use java-style namespacing, e.g. com.abc.alias
    """
    INPUT_EXTENSIONS = [".*"]
    OUTPUT_EXTENSIONS = [".*"]
    ALIASES = ['dexy', '']

### @export "setup"
    @classmethod
    def setup(klass, doc, artifact_key, previous_artifact = None, next_handler = None):
        h = klass()
        h.doc = doc
        h.artifact = Artifact.setup(doc, artifact_key, h, previous_artifact)
        if next_handler:
            h.artifact.next_handler_name = next_handler.__name__

        # Determine file extension.
        ext = previous_artifact.ext
        if set([ext, ".*"]).isdisjoint(set(h.INPUT_EXTENSIONS)):
            exception_text = """Extension %s is not supported.
            Supported extensions are: %s""" % (ext, ', '.join(h.INPUT_EXTENSIONS))
            raise Exception(exception_text)
        h.ext = ext
        
        if ".*" in h.OUTPUT_EXTENSIONS:
            h.artifact.ext = ext
        else:
            if next_handler and not ".*" in next_handler.INPUT_EXTENSIONS:
                for e in h.OUTPUT_EXTENSIONS:
                    if e in next_handler.INPUT_EXTENSIONS:
                        h.artifact.ext = e
                
                if not h.artifact.ext:
                    raise Exception("No compatible input extension found in next handler.")
            else:
                h.artifact.ext = h.OUTPUT_EXTENSIONS[0]
    
        h.artifact.set_hashstring()
        if hasattr(dexy.logger.log, 'getChild'):
            # This adds a nice namespacing, only available in Python 2.7
            h.log = dexy.logger.log.getChild(klass.__name__)
        else:
            h.log = dexy.logger.log
        return h

### @export "process"
    def process(self):
        """This is the method that does the "work" of the handler, that is
        filtering the input and producing output. This method can be overridden
        in a subclass, or one of the convenience methods named below can be
        implemented and will be delegated to. If more than 1 convenience method
        is implemented then an exception will be raised."""
        method_used = None

        if hasattr(self, "process_text"):
            if method_used:
                raise Exception("%s has already been called" % method_used)
            input_text = self.artifact.input_text()
            output_text = self.process_text(input_text)
            self.artifact.data_dict['1'] = output_text
            method_used = "process_text"

        if hasattr(self, "process_dict"):
            if method_used:
                raise Exception("%s has already been called" % method_used)
            input_dict = self.artifact.input_data_dict
            output_dict = self.process_dict(input_dict)
            self.artifact.data_dict = output_dict
            method_used = "process_dict"

        if hasattr(self, "process_text_to_dict"):
            if method_used:
                raise Exception("%s has already been called" % method_used)
            input_text = self.artifact.input_text()
            output_dict = self.process_text_to_dict(input_text)
            self.artifact.data_dict = output_dict
            method_used = "process_text_to_dict"
        
        if not method_used:
            self.artifact.data_dict = self.artifact.input_data_dict
            method_used = "process"
        
        return method_used

### @export "set-input-text"
    def set_input_text(self, input_text):
        if hasattr(self, 'artifact'):
            raise Exception("already have an artifact!")
        self.artifact = Artifact()
        self.artifact.input_data_dict = {'1' : input_text}
        self.artifact.data_dict = OrderedDict()

### @export "generate"
    def generate(self):
        self.artifact.generate()

### @export "generate-artifact"
    def generate_artifact(self): 
        start = time.time()

        if self.artifact.dj_file_exists():
            method = 'cached'
            self.artifact.load_dj()
        else:
            method = 'generated'
            self.process()
            self.generate()

        finish = time.time()
        self.log_time(start, finish, method)

        return self.artifact

### @export "log-time"
    def log_time(self, start, finish, method):
        doc = self.artifact.doc

        elapsed = finish - start
        row = [
            self.artifact.key,
            self.artifact.hashstring,
            doc.key(),
            self.__class__.__name__,
            method,
            start, 
            finish, 
            elapsed
        ]
        self.artifact.doc.controller.log_time(row)