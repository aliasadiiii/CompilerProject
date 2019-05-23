from collections import defaultdict

from scanner import tokenize, ScannerException


class ParserException(Exception):
    def __init__(self, message):
        self.message = message
        super(ParserException, self).__init__()


class Diagram(object):
    def __init__(self, grammars, first_set, follow_set):
        self.non_terminals = non_terminals
        self.actions = actions
        self.accept_states = accept_states
        self.first_set = first_set
        self.follow_set = follow_set
        self.stack = [('program', 0)]  # list of pair (non_terminal, state)
        self.parse_tree = [('program', 0)]

    def move_forward(self, terminal):
        last_non_terminal, last_state = self.stack[-1]
        if last_state == self.accept_states[last_non_terminal]:
            self.stack.pop()
            return False

        for key, value in self.actions[last_non_terminal][last_state]:
            if key not in self.non_terminals:
                if key == 'eps' and terminal in \
                        self.follow_set[last_non_terminal]:
                    self.stack[-1] = (last_non_terminal, value)
                    return False

                if key == terminal:
                    self.stack[-1] = (last_non_terminal, value)
                    self.parse_tree.append((value, len(self.stack)))
                    return True
                continue

            if terminal in self.first_set[key] or \
                    ('eps' in self.first_set[key] and
                     terminal in self.follow_set[key]):
                self.stack[-1] = (last_non_terminal, value)
                self.parse_tree.append((value, len(self.stack)))
                self.stack.append((key, 0))
                return False

        key, value = self.actions[last_non_terminal][last_state].items()[0]
        if key not in self.non_terminals:
            raise ParserException(message="Syntax Error! Missing #%s" % key)
        else:
            if terminal in self.follow_set[key]:
                self.stack[-1] = (last_non_terminal, value)
                self.parse_tree.append((value, len(self.stack)))
                self.stack.append((key, 0))
                raise ParserException(message="Syntax Error! Missing #%s" % key)

            raise ParserException(message="Syntax Error! Unexpected #%s" %
                                          terminal)


class Parser(object):
    def __init__(self, diagram):
        self.diagram = diagram

    def parse(self, input_str):
        pointer = 0
        scanner_errors = defaultdict(list)
        parser_errors = defaultdict(list)

        number_of_failure = 0
        while pointer < len(input_str):
            line_number = input_str[0:pointer].count('\n')
            try:
                token_type, token = tokenize(input_str, pointer)
                if token_type in ['W', 'COMMENT']:
                    continue

                terminal = token if token_type in ['SYMBOL', 'KEYWORD'] \
                    else token_type

                try:
                    while not self.diagram.move_forward(terminal):
                        pass
                    number_of_failure = 0
                except ParserException as e:
                    parser_errors[line_number].append(e.message)
                    number_of_failure = number_of_failure + 1

            except ScannerException as e:
                token = e.message
                scanner_errors[line_number].append(token)
            pointer += len(token)

        try:
            while not self.diagram.move_forward('$'):
                pass
        except ParserException:
            line_number = input_str.count('\n')
            if number_of_failure > 0:
                parser_errors[line_number].append(
                    "Syntax Error! Unexpected EndOfFile")
            else:
                parser_errors[line_number].append(
                    "Syntax Error! Malformed Input")

        return self.diagram.parse_tree, scanner_errors, parser_errors


def parse_file(input_file, grammar_file, first_set_file, follow_set_file,
               output_file, error_file):
    with open(input_file) as f:
        input_str = f.read()

    with open(grammar_file) as f:
        grammars = f.readlines()
    with open(first_set_file) as f:
        first_set = f.readlines()
    with open(follow_set_file) as f:
        follow_set = f.readlines()

    diagram = Diagram(grammars, first_set, follow_set)
    parser = Parser(diagram)
    parse_tree, scanner_errors, parser_errors = parser.parse(input_str)

    with open(output_file, 'w') as f:
        for action, level in parse_tree:
            output = '|' * level + action
            f.write(output + '\n')

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
