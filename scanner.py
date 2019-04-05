from collections import defaultdict
import re


class ScannerException(Exception):
    pass


def tokenize_pattern(input_str, pointer, pattern):
    used_chars = 0
    regex = re.compile(pattern, flags=re.DOTALL)
    result = ''

    while pointer + used_chars < len(input_str):
        char = input_str[pointer + used_chars]
        tmp = result + char

        if regex.fullmatch(tmp) is not None:
            result = tmp
            used_chars += 1
        else:
            break

    return used_chars, result


def tokenize_comment(input_str, pointer):
    return tokenize_pattern(input_str, pointer, r'/\*.*\*/|//.*\n')


def tokenize_number(input_str, pointer):
    return tokenize_pattern(input_str, pointer, r'[0-9]+')


def tokenize_identifier(input_str, pointer):
    return tokenize_pattern(input_str, pointer, r'[a-zA-Z][a-zA-Z0-9]*')


def tokenize_keyword(input_str, pointer):
    used_chars, result = tokenize_identifier(input_str, pointer)
    keywords = ['if', 'else', 'void', 'int', 'while', 'break', 'continue'
                                                               'switch',
                'default', 'case', 'return']
    for keyword in keywords:
        if result == keyword:
            return used_chars, result
    return 0, ''


def tokenize_symbol(input_str, pointer):
    return tokenize_pattern(input_str, pointer,
                            r'\;|\:|\,|\[|\]|\(|\)|\{|\}|\+|\-|\*|\=|\=|\<|\=\=')


def skip_whitespace(input_str, pointer):
    return tokenize_pattern(input_str, pointer, '(\r|\t|\v|\f| )*\n?')


def _tokenize(input_str, pointer):
    tokenizers = [(tokenize_keyword, 'KEYWORD'),
                  (tokenize_comment, 'COMMENT'),
                  (tokenize_identifier, 'ID'),
                  (tokenize_number, 'NUM'),
                  (skip_whitespace, 'W'),
                  (tokenize_symbol, 'SYMBOL')]

    for tokenizer, token_type in tokenizers:
        used_chars, result = tokenizer(input_str, pointer)
        if used_chars > 0:
            return token_type, result

    raise ScannerException()


def tokenize_file(input_file, output_file, error_file):
    with open(input_file) as f:
        input_str = f.read()

    tokens = defaultdict(list)
    errors = defaultdict(list)
    pointer = 0

    while pointer < len(input_str):
        line_number = input_str[0:pointer].count('\n')
        try:
            token_type, token = _tokenize(input_str, pointer)
            if token_type != 'W':
                tokens[line_number].append((token_type, token))
        except ScannerException:
            token = input_str[pointer]
            errors[line_number].append((token, 'invalid input'))

        pointer += len(token)

    with open(output_file, 'w') as f:
        max_length = max(tokens.keys()) + 1
        for i in range(max_length):
            output = '%s.' % (i+1)
            for token in tokens[i]:
                output += ' %s' % str(token)
            f.write(output + '\n')

    with open(error_file, 'w') as f:
        if errors:
            max_length = max(errors.keys()) + 1
            for i in range(max_length):
                output = '%s.' % (i+1)
                for error in errors[i]:
                    output += ' %s' % str(error)
                f.write(output + '\n')
