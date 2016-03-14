import sys
import base64
from jnius import autoclass, cast
from pysb import bng, Initial, Parameter
from TripsModule import trips_module

KQMLPerformative = autoclass('TRIPS.KQML.KQMLPerformative')
KQMLList = autoclass('TRIPS.KQML.KQMLList')
KQMLObject = autoclass('TRIPS.KQML.KQMLObject')

from mea import MEA

class InvalidModelException(Exception):
    def __init__(self,*args,**kwargs):
            Exception.__init__(self,*args,**kwargs)

class MEA_Module(trips_module.TripsModule):
    def __init__(self, argv):
        super(MEA_Module, self).__init__(argv)
        self.tasks = ['SIMULATE-MODEL']

    def init(self):
        '''
        Initialize TRIPS module
        '''
        super(MEA_Module, self).init()
        # Send subscribe messages
        for task in self.tasks:
            msg_txt = '(subscribe :content (request &key :content (%s . *)))' % task
            self.send(KQMLPerformative.fromString(msg_txt))
        # Instantiate a singleton MEA agent
        self.mea = MEA()
        self.ready()

    def receive_request(self, msg, content):
        '''
        If a "request" message is received, decode the task and the content
        and call the appropriate function to prepare the response. A reply 
        "tell" message is then sent back.
        '''
        content_list = cast(KQMLList, content)
        task_str = content_list.get(0).toString().upper()
        if task_str == 'SIMULATE-MODEL':
            reply_content = self.respond_simulate_model(content_list)
        else:
            self.error_reply(msg, 'unknown request task ' + task_str)
            return

        reply_msg = KQMLPerformative('reply')
        reply_msg.setParameter(':content', cast(KQMLObject, reply_content))
        self.reply(msg, reply_msg)

    def respond_simulate_model(self, content_list):
        '''
        Response content to simulate-model request
        '''
        model_str = content_list.getKeywordArg(':model')
        if model_str is not None:
            model_str = model_str.toString()
            try:
                model = self.decode_model(model_str[1:-1])
            except InvalidModelException:
                reply_content =\
                    KQMLList.fromString('(FAILURE :reason INVALID_MODEL)')
                return reply_content
        target_entity = content_list.getKeywordArg(':target_entity')
        if target_entity is not None:
            target_entity = target_entity.toString()[1:-1]
        else:
            reply_content =\
                KQMLList.fromString('(FAILURE :reason MISSING_PARAMETER)')
            return reply_content
        target_pattern = content_list.getKeywordArg(':target_pattern')
        if target_pattern is not None:
            target_pattern = target_pattern.toString().lower()
        else:
            reply_content =\
                KQMLList.fromString('(FAILURE :reason MISSING_PARAMETER)')
            return reply_content
        condition_entity = content_list.getKeywordArg(':condition_entity')
        if condition_entity is not None:
            condition_entity = condition_entity.toString()
        condition_type = content_list.getKeywordArg(':condition_type')
        if condition_type is not None:
            condition_type = condition_type.toString()

        print condition_entity, condition_type, target_entity, target_pattern

        self.get_context(model)
        print model.species
        if condition_entity is None:
            target_match = self.mea.check_pattern(model, target_entity,
                                                  target_pattern)
        else:
            target_match = self.mea.compare_conditions(model, target_entity,
                                                       target_pattern,
                                                       condition_entity,
                                                       condition_type)
        target_match_str = 'TRUE' if target_match else 'FALSE'
        reply_content = KQMLList()
        reply_content.add('SUCCESS :content (:target_match %s)' % target_match_str)
        return reply_content

    @staticmethod
    def get_context(model):
        # TODO: Here we will have to query the context
        kras = model.monomers['KRAS']
        p = Parameter('kras_act_0', 100)
        model.add_component(p)
        model.initial(kras(act='active'), p)

    @staticmethod
    def decode_model(model_enc_str):
        try:
            model_str = base64.b64decode(model_enc_str)
        except:
            raise InvalidModelException 
        model = MEA_Module.model_from_string(model_str)
        return model

    @staticmethod
    def model_from_string(model_str):
        with open('tmp_model.py', 'wt') as fh:
            fh.write(model_str)
        from tmp_model import model
        return model

if __name__ == "__main__":
    MEA_Module(['-name', 'MEA'] + sys.argv[1:]).run()

