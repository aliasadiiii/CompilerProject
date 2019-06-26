from collections import defaultdict

from intermediate_code_generator import IntermediateCodeGenerator, SemanticException
from scanner import tokenize, ScannerException


class ParserException(Exception):
    def __init__(self, message):
        self.message = message
        super(ParserException, self).__init__()


class ParserExceptionWithoutSkip(Exception):
    def __init__(self, message):
        self.message = message
        super(ParserExceptionWithoutSkip, self).__init__()


class Diagram(object):
    def __init__(self, grammar, first_set, follow_set):
        self.non_terminals = grammar.keys()

        self.actions = {}
        self.accept_states = {}
        for non_terminal in grammar.keys():
            graph, accept_state = Diagram.create_graph(grammar[non_terminal])
            self.actions[non_terminal] = graph
            self.accept_states[non_terminal] = accept_state

        self.first_set = first_set
        self.follow_set = follow_set
        self.stack = [('Program', 0)]  # list of pair (non_terminal, state)
        self.parse_tree = [('Program', 0)]

        self.intermediate_code_generator = IntermediateCodeGenerator()

    @staticmethod
    def create_graph(rules):
        graph = defaultdict(dict)
        current_state = 2
        for rule in rules:
            last_state = 0
            for part in rule[:-1]:
                graph[last_state].update({part: current_state})
                last_state = current_state
                current_state += 1
            graph[last_state].update({rule[-1]: 1})
        return graph, 1

    def move_forward(self, terminal, token):
        last_non_terminal, last_state = self.stack[-1]
        if last_state == self.accept_states[last_non_terminal]:
            self.stack.pop()
            return False

        for key, value in self.actions[last_non_terminal][last_state].items():
            if key.startswith('#'):
                self.stack[-1] = (last_non_terminal, value)
                self.intermediate_code_generator.run_routine(key[1:])
                return False

            if key not in self.non_terminals:
                if key == 'eps' and terminal in \
                        self.follow_set[last_non_terminal]:
                    self.stack[-1] = (last_non_terminal, value)
                    return False

                if key == terminal:
                    if key in ('int', 'void', 'ID'):
                        self.intermediate_code_generator.semantic_stack.append(
                            token)
                    if key == 'NUM':
                        self.intermediate_code_generator.semantic_stack.append(
                            '#%s' % token
                        )

                    self.stack[-1] = (last_non_terminal, value)
                    self.parse_tree.append((key, len(self.stack)))
                    return True
                continue

            if terminal in self.first_set[key] or \
                    ('eps' in self.first_set[key] and
                     terminal in self.follow_set[key]):
                self.stack[-1] = (last_non_terminal, value)
                self.parse_tree.append((key, len(self.stack)))
                self.stack.append((key, 0))
                return False

        key, value = list(self.actions[last_non_terminal]
                          [last_state].items())[0]
        if key not in self.non_terminals:
            self.stack[-1] = (last_non_terminal, value)
            raise ParserExceptionWithoutSkip(
                message="Syntax Error! Missing #%s" % key)
        else:
            if terminal in self.follow_set[key]:
                self.stack[-1] = (last_non_terminal, value)
                raise ParserExceptionWithoutSkip(
                    message="Syntax Error! Missing #%s" % key)

            raise ParserException(message="Syntax Error! Unexpected #%s" %
                                          terminal)


class Parser(object):
    def __init__(self, diagram):
        self.diagram = diagram

    def parse(self, input_str):
        pointer = 0
        scanner_errors = defaultdict(list)
        parser_errors = defaultdict(list)
        semantic_errors = defaultdict(list)

        number_of_failure = 0
        while pointer < len(input_str):
            line_number = input_str[0:pointer].count('\n')
            try:
                token_type, token = tokenize(input_str, pointer)
                if token_type in ['W', 'COMMENT']:
                    pointer += len(token)
                    continue

                terminal = token if token_type in ['SYMBOL', 'KEYWORD'] \
                    else token_type

                try:
                    while True:
                        try:
                            if self.diagram.move_forward(terminal, token):
                                break
                        except ParserExceptionWithoutSkip as e:
                            parser_errors[line_number].append(e.message)
                            number_of_failure = number_of_failure + 1
                        except SemanticException as e:
                            semantic_errors[line_number].append(e.message)
                            self.diagram.intermediate_code_generator.is_ok = False
                    number_of_failure = 0
                except ParserException as e:
                    parser_errors[line_number].append(e.message)
                    number_of_failure = number_of_failure + 1

            except ScannerException as e:
                token = e.message
                scanner_errors[line_number].append(token)
            pointer += len(token)

        try:
            while not self.diagram.move_forward('$', '$'):
                pass
        except SemanticException as e:
            line_number = input_str.count('\n')
            semantic_errors[line_number].append(e.message)
            self.diagram.intermediate_code_generator.is_ok = False
        except ParserException:
            line_number = input_str.count('\n')
            if number_of_failure > 0:
                parser_errors[line_number].append(
                    "Syntax Error! Unexpected EndOfFile")
            else:
                parser_errors[line_number].append(
                    "Syntax Error! Malformed Input")

        return self.diagram.intermediate_code_generator.program_block, scanner_errors, parser_errors, semantic_errors


def parse_file(input_file, grammar_file, first_set_file, follow_set_file,
               output_file, error_file):
    with open(input_file) as f:
        input_str = f.read()

    with open(grammar_file) as f:
        rules = f.readlines()
        grammar = defaultdict(list)
        for rule in rules:
            rule = rule.split('\n')[0].strip()
            lhs, rhs = rule.split(' -> ')
            grammar[lhs] = [rr.split(' ') for rr in rhs.split(' | ')]

    with open(first_set_file) as f:
        lines = f.readlines()
        first_set = defaultdict(list)
        for line in lines:
            line = line.split('\n')[0].strip()
            lhs, *rhs = line.split(' ')
            first_set[lhs] = rhs

    with open(follow_set_file) as f:
        lines = f.readlines()
        follow_set = defaultdict(list)
        for line in lines:
            line = line.split('\n')[0].strip()
            lhs, *rhs = line.split(' ')
            follow_set[lhs] = rhs

    diagram = Diagram(grammar, first_set, follow_set)
    parser = Parser(diagram)
    program_block, scanner_errors, parser_errors, semantic_errors = parser.parse(input_str)

    with open(output_file, 'w') as f:
        def xstr(x):
            if x is None:
                return ''
            return x
        for i, inst in enumerate(program_block):
            if len(inst) != 4:
                inst = (None, None, None, None)
            f.write('%s\t(%s,%s,%s,%s)\n' % (i, inst[0] or '', xstr(inst[1]), xstr(inst[2]), xstr(inst[3])))

    with open(error_file, 'w') as f:
        if scanner_errors:
            for i in scanner_errors.keys():
                output = '%s.' % (i + 1)
                for error in scanner_errors[i]:
                    output += ' %s' % str(error)
                f.write(output + '\n')

        if parser_errors:
            for i in parser_errors.keys():
                output = '%s.' % (i + 1)
                for error in parser_errors[i]:
                    output += ' %s' % str(error)
                f.write(output + '\n')

        if semantic_errors:
            for i in semantic_errors.keys():
                output = '%s.' % (i + 1)
                for error in semantic_errors[i]:
                    output += ' %s' % str(error)
                f.write(output + '\n')
