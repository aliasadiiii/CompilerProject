from parser import parse_file

if __name__ == '__main__':
    parse_file('input.txt', 'grammar.txt', 'first_set.txt', 'follow_set.txt',
               'scanner.txt', 'lexical_errors.txt')
