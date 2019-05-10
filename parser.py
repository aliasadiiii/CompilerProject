from collections import defaultdict

from scanner import tokenize, ScannerException


class ParserException(Exception):
    def __init__(self, message):
        self.message = message
        super(ParserException, self).__init__()


class Parser(object):
    def __init__(self, non_terminals, actions, accept_states, first_set,
                 follow_set):
        self.non_terminals = non_terminals
        self.actions = actions
        self.accept_states = accept_states
        self.first_set = first_set
        self.follow_set = follow_set
        self.stack = []  # list of pair (non_terminal, state)
        self.parse_tree = []

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

    def parse(self, input_str):
        pointer = 0
        parse_tree = [('A', 0)]
        errors = defaultdict(list)
        self.stack = [('program', 0)]

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
                    while not self.move_forward(terminal):
                        pass
                    number_of_failure = 0
                except ParserException as e:
                    errors[line_number].append((e.message, 'invalid input'))
                    number_of_failure = number_of_failure + 1

            except ScannerException as e:
                token = e.message
                errors[line_number].append((token, 'invalid input'))
            pointer += len(token)

        try:
            while not self.move_forward('$'):
                pass
        except ParserException:
            line_number = input_str.count('\n')
            if number_of_failure > 0:
                errors[line_number].append(
                    ("Syntax Error! Unexpected EndOfFile", 'invalid input'))
            else:
                errors[line_number].append(
                    ("Syntax Error! Malformed Input", 'invalid input'))

        return parse_tree, errors


def parse_file(input_file, output_file, error_file):
    with open(input_file) as f:
        input_str = f.read()

    parser = Parser()
    parse_tree, errors = parser.parse(input_str)

    with open(output_file, 'w') as f:
        for action, level in parse_tree:
            output = '|' * level + action
            f.write(output + '\n')

    with open(error_file, 'w') as f:
        if errors:
            for i in errors.keys():
                output = '%s.' % (i + 1)
                for error in errors[i]:
                    output += ' %s' % str(error)
                f.write(output + '\n')
