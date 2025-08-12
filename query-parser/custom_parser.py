from lark import Lark, Transformer, v_args

class ValidationError(Exception):
    def __init__(self, message, error_type="Syntax", details=None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}

@v_args(inline=True)
class CustomSqlTransformer(Transformer):
    def create_model_statement(self, *args):
        return {'create_model': {'model_name': str(args[0]), 'options': args[1] or {}, 'query': args[2]}}

    def ml_predict_statement(self, *args):
        return {'ml_predict': {'model_name': str(args[1]), 'query': args[2]}}

    def options_clause(self, *options):
        return options

    def model_options(self, *options):
        return dict(options)

    def option(self, key, value):
        # Remove quotes from ESCAPED_STRING or SINGLE_QUOTED_STRING
        if hasattr(value, 'type') and (value.type == 'ESCAPED_STRING' or value.type == 'SINGLE_QUOTED_STRING'):
            value = value[1:-1]
        return (str(key), value)

    def sql_query(self, query_token):
        return query_token.value.strip()

custom_sql_grammar = r'''
    ?start: (create_model_statement | ml_predict_statement) [";"]

    create_model_statement: CREATE MODEL CNAME options_clause AS "(" sql_query ")"
    options_clause: OPTIONS "(" [model_options] ")"

    ml_predict_statement: SELECT "*" FROM ML_PREDICT
    from_ml_predict: ML_PREDICT "(" MODEL CNAME "," "(" sql_query ")" ")"

    model_options: option ("," option)*
    option: CNAME "=" value
    value: ESCAPED_STRING | SINGLE_QUOTED_STRING

    SINGLE_QUOTED_STRING: /'[^']*'/

    sql_query: /[^)]+/

    CREATE: "CREATE"i
    MODEL: "MODEL"i
    OPTIONS: "OPTIONS"i
    AS: "AS"i
    SELECT: "SELECT"i
    FROM: "FROM"i
    ML_PREDICT: "ML.PREDICT"i

    %import common.CNAME
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
'''

custom_sql_parser = Lark(custom_sql_grammar, start='start', parser='lalr', transformer=CustomSqlTransformer())