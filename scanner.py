import string


class ScannerException(Exception):
    def __init__(self, message):
        self.message = message
        super(ScannerException, self).__init__()


class DFAException(Exception):
    pass


def is_valid(char):
    if char.isalpha():
        return True

    if char.isdigit():
        return True

    return char in ['*', '=', '/', '[', ']', '{', '}', '(', ')', ':', ';', ',',
                    '<', '+', '-', '\n', ' ', '\t', '\r', '\f', '\v']


class DFA(object):
    def __init__(self, start_state, transition_function, accept_states):
        self.current_state = start_state
        self.transition_function = transition_function
        self.accept_states = accept_states

    def next_state(self, char):
        for key in self.transition_function.keys():
            if self.current_state == key[0] and char in key[1]:
                self.current_state = self.transition_function[key]
                return True

        if not is_valid(char):
            raise DFAException()

        return False

    def is_accepted(self):
        return self.current_state in self.accept_states


def tokenize_pattern(token_type, input_str, pointer, dfa):
    used_chars = 0
    result = ''

    while pointer + used_chars < len(input_str):
        char = input_str[pointer + used_chars]
        try:
            done = dfa.next_state(char)
            if not done:
                break

            used_chars += 1
            result += char
        except DFAException:
            if token_type == 'W':
                break
            result += char
            raise ScannerException(result)

    if dfa.is_accepted() or used_chars == 0:
        return used_chars, result
    else:
        if pointer + used_chars < len(input_str):
            result += input_str[pointer + used_chars]
        raise ScannerException(result)


def tokenize_comment(token_type, input_str, pointer):
    dfa = DFA(
        start_state=0,
        transition_function={
            (0, '/'): 1,
            (1, '/'): 2,
            (2, '\n'): 3,
            (2, string.printable.replace('\n', '')): 2,
            (1, '*'): 4,
            (4, '*'): 5,
            (5, '*'): 5,
            (5, '/'): 6,
            (4, string.printable.replace('/', '').replace('*', '')): 4,
            (5, string.printable.replace('/', '')): 4
        },
        accept_states=[3, 6]
    )
    return tokenize_pattern(token_type, input_str, pointer, dfa)


def tokenize_number(token_type, input_str, pointer):
    dfa = DFA(
        start_state=0,
        transition_function={
            (0, string.digits): 0
        },
        accept_states=[0]
    )

    return tokenize_pattern(token_type, input_str, pointer, dfa)


def tokenize_identifier(token_type, input_str, pointer):
    dfa = DFA(
        start_state=0,
        transition_function={
            (0, string.ascii_letters): 1,
            (1, string.ascii_letters + string.digits): 1
        },
        accept_states=[1]
    )

    return tokenize_pattern(token_type, input_str, pointer, dfa)


def tokenize_keyword(token_type, input_str, pointer):
    try:
        used_chars, result = tokenize_identifier(token_type, input_str, pointer)
    except ScannerException:
        return 0, ''

    keywords = ['if', 'else', 'void', 'int', 'while', 'break', 'continue',
                'switch', 'default', 'case', 'return']
    for keyword in keywords:
        if result == keyword:
            return used_chars, result
    return 0, ''


def tokenize_symbol(token_type, input_str, pointer):
    dfa = DFA(
        start_state=0,
        transition_function={
            (0, ';:,[](){}+-*<'): 1,
            (0, '='): 2,
            (2, '='): 1
        },
        accept_states=[1, 2]
    )
    return tokenize_pattern(token_type, input_str, pointer, dfa)


def skip_whitespace(token_type, input_str, pointer):
    dfa = DFA(
        start_state=0,
        transition_function={
            (0, '\r\f\v\t\n '): 0
        },
        accept_states=[0]
    )

    return tokenize_pattern(token_type, input_str, pointer, dfa)


def tokenize(input_str, pointer):
    tokenizers = [(tokenize_keyword, 'KEYWORD'),
                  (tokenize_comment, 'COMMENT'),
                  (tokenize_identifier, 'ID'),
                  (tokenize_number, 'NUM'),
                  (skip_whitespace, 'W'),
                  (tokenize_symbol, 'SYMBOL')]

    for tokenizer, token_type in tokenizers:
        used_chars, result = tokenizer(token_type, input_str, pointer)
        if used_chars > 0:
            return token_type, result

    raise ScannerException(input_str[pointer])
