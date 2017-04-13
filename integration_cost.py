#!/usr/bin/env python

"""
Based on Asad's IntegrationCost-Dundee-fixed.py
Should be functional for Dundee and for Mary
Definitely works for plain SENTS files, as a replacement for
IntegrationCost-Stories.py
"""

# Python 2/3 compatibility imports
from __future__ import print_function

# Imports
import sys
import re
from subprocess import Popen, PIPE

# Configuration variables
PARSER_INVOCATION = "java -Xmx2g -cp StanfordParser/stanford-parser.jar:" \
                    "StanfordParser/stanford-parser-2012-05-22-models.jar: " \
                    "InvokeStanfordParser"
discourse_ref_pos_tags = []
past_participle_intransitive_verbs = ['gone']  # We might want to expand this
possible_aux = ['VBP', 'VBD', 'VBG', 'VBZ', 'VBN', 'VB', 'NN', 'NNP', 'NNS']
verbs = ['VBP', 'VBD', 'VBG', 'VBZ', 'VBN', 'VB']
punctuation_corpus = [",", ".", "\"", "...", "!", "?", ";", "``", "\'\'", "'s", "'d", "n\'t"]
# Original version for Dundee-fixed
# punctuation_corpus = [",", "\"", "...", ";", "``", "\'\'", "'s", "'d", "n\'t"]

INTERMEDIATE_FILENAME = 'integration_cost.tmp.csv'


# Class Definitions
class ParseStructure(object):
    def __init__(self, pos_tags, dependencies, verbose=False):
        self.words = []
        self.insert_words(pos_tags)
        for dependency in dependencies.split("\n"):
            if len(dependency) > 0:
                if verbose:
                    print(dependency)
                self.map_dependency(dependency)
        if verbose:
            print()

    def insert_words(self, pos_tags):
        new_word = Word(0, "ROOT", "root")
        self.words.append(new_word)
        elements = pos_tags.split()
        counter = 1
        for element in elements:
            parts = element.split("/")
            word = "\"" + parts[0] + "\""
            pos = parts[1]
            new_word = Word(counter, word, pos)
            self.words.append(new_word)
            counter += 1

    # Map the dependency into the parse_structure
    def map_dependency(self, dependency):
        relation, governor, dependent = get_elements(dependency)
        self.words[governor].out_edges.append([dependent, relation])
        self.words[dependent].in_edges.append([governor, relation])

    def set_referents(self):
        for word in self.words:
            word.det_disc_ref()

    def solve_coordination(self):
        # Check each word
        for word in self.words:
            # Check if there is a coordination edge
            for dependent in word.out_edges:
                # Check if it is "and"
                if dependent[1] == 'cc' and self.words[dependent[0]].text == '"and"':
                    for dependent2 in word.out_edges:
                        # Identify which one is the other element of the coordination
                        if dependent2[1] == 'conj':
                            # Copy dependencies to the other element
                            for governor in word.in_edges:
                                position = governor[0]
                                relation = governor[1]
                                self.words[dependent2[0]].in_edges.append(governor)
                                self.words[position].out_edges.append([dependent2[0], relation])

    # This output mode is used for the gold stories
    def print_parse_structure_two(self, file_stream):
        """An additional parse structure method. I have no idea why this is here. -DMH"""
        out_line = ""
        punctuation = ["ROOT", "TRACE", "\",\"", "\".\"", "\"\"\"", "\"...\"", "\"!\"", "\"?\"", "\";\"", "\"``\"",
                       "\'\'", "\"'s\"", "\"\'\'\"", "\"'d\"", "\"n\'t\""]
        for word in self.words:
            if word.text not in punctuation:
                out_line += word.text + ","
                if word.disc_ref:
                    out_line += "1,"
                else:
                    out_line += ","
                if word.disc_refs > 0:
                    out_line += str(word.disc_refs) + "\n"
                else:
                    out_line += ",\n"
        file_stream.write(out_line)

    # Output mode for the Mary Corpus
    def print_parse_structure_mary(self, file_stream, file_lines):
        max_index = len(file_lines)
        counter = 0
        out_line = []
        punctuation = ["ROOT", "TRACE", "\"\"\"", "\"...\"", "\"``\"", "\"\'\'\"", "\"_\"", "\"\'\"", "\"`\""]
        contractions = ["\"\'s\"", "\"'d\"", "\"n\'t\"", "\"\'ve\"", "\"\'ll\"", "\"\'re\"", "\"\'m\""]
        for word in self.words:
            # Discard all punctuation marks
            if word.text not in punctuation:
                if (((word.text not in contractions) and
                        not (word.text == "\"not\"" and
                             previous_word == "\"can\"" and
                             file_lines[counter - 1][3] == "cannot")) or
                    ((word.text in contractions) and (previous_word == "\"_\"") and
                     (file_lines[counter][3] == "_" + word.text.replace("\"", "")))):
                    if word.text in contractions:
                        new_line = ["\"_" + word.text.replace("\"", "") + "\""]
                    else:
                        new_line = [word.text]
                    if word.disc_ref:
                        new_line.append(1)
                    else:
                        new_line.append(0)
                    new_line.append(word.disc_refs)
                    if max_index > counter and "\"" + file_lines[counter][3] + "\"" != new_line[0]:
                        # if we don't find the target
                        if not add_suffix_prefix(punctuation, word.text, file_lines[counter][3]):
                            new_line.append("MISMATCH!!")
                        # if we DID, we just put the result
                        else:
                            new_line[0] = "\"" + file_lines[counter][3] + "\""
                    out_line.append(new_line)
                    counter += 1
                else:
                    if word.text == "\"\'s\"" and previous_word == "\"_\"" and file_lines[counter - 1][3] != "\"_\'s\"":
                        if file_lines[counter - 1][3] == out_line[counter - 1][0].replace("\"", "") + "_\'s":
                            new_line = ["\"" + out_line[counter - 1][0].replace("\"", "") + "_\'s\""]
                    else:
                        new_line = [
                            "\"" + out_line[counter - 1][0].replace("\"", "") + word.text.replace("\"", "") + "\""]
                    if word.disc_ref:
                        new_line.append(out_line[counter - 1][1] + 1)
                    else:
                        new_line.append(out_line[counter - 1][1])

                    new_line.append(out_line[counter - 1][2] + word.disc_refs)
                    if "\"" + file_lines[counter - 1][3] + "\"" != new_line[0]:
                        new_line.append("MISMATCH!!2")
                    out_line[counter - 1] = new_line
            previous_word = word.text
        if counter != max_index:
            out_line[counter - 1].append("INDEX\t MISMATCH")
        print_list(out_line, file_stream)

    def print_parse_structure_dundee_beta(self, file_stream, file_lines):
        max_index = len(file_lines)
        counter = 0
        out_line = []
        punctuation = ["ROOT", "TRACE", "\"\"\"", "\"``\"", "\"\'\'\"", "\"_\"", "\"`\"", ")",
                       "("]  # "\"\'\"", "\"...\""  consistent with SP
        special_tokens = ["\'\'"]  # ,"-LRB-\r\n","-RRB-\r\n" are consistent with stanford parsers output
        for word in self.words:
            if max_index > counter and file_lines[counter][0] in special_tokens:
                out_line.append([file_lines[counter][0].replace("\r\n", "")])
                counter += 1
                print("found special symbol" + str(counter) + file_lines[counter - 1][0])
            # Discard all punctuation marks
            if word.text not in punctuation:
                if not (word.text == "\"not\"" and previous_word == "\"can\""
                        and file_lines[counter - 1][0] == "cannot"):
                    new_line = [word.text]
                    if word.disc_ref:
                        new_line.append(1)
                    else:
                        new_line.append(0)
                    new_line.append(word.disc_refs)
                    if max_index > counter and "\"" + file_lines[counter][0].replace("\r\n", "") + "\"" != new_line[0]:
                        # if we don't find the target
                        if not add_suffix_prefix(punctuation, word.text,
                                                 file_lines[counter][0]):
                            new_line.append("MISMATCH!!" + new_line[0] + " " + file_lines[counter][0])
                            print(new_line[0])
                            print(file_lines[counter][0])
                            print("MISMATCH")

                        # if we DID, we just put the result
                        else:
                            new_line[0] = "\"" + file_lines[counter][0] + "\""
                    out_line.append(new_line)
                    counter += 1
                else:
                    out_line[counter - 1][0] = "\"cannot\""
                    out_line[counter - 1][3] = ""

            previous_word = word.text
        if counter != max_index:
            out_line[counter - 1].append("INDEX\t MISMATCH")
        print_list(out_line, file_stream)

    def print_parse_structure_dundee(self, file_stream, sentence, alignment_file):
        sentence = sentence.rstrip()
        sent_parts = sentence.split(" ")

        print(sent_parts)
        print("SETNENEN:", sentence)
        file_lines = []

        # Last token of the sentence, normally it should be "." "?" or "!"
        last_token = sent_parts[len(sent_parts) - 1]
        # second to last token of the sentence
        penultimate_token = sent_parts[len(sent_parts) - 2]

        if len(sent_parts) > 2:

            if len(sent_parts) == 3:
                first_align_word = ""
            else:
                first_align_line = alignment_file.readline()  # Get the first line of the align file.
                first_align_line = first_align_line.rstrip("\r\n")
                first_align_word = first_align_line.split("\t")[0]  # Identify its words associated
                file_lines.append(
                    first_align_line.split("\t"))  # Add to the list of lines corresponding to the sentence

            sec_align_line = alignment_file.readline().rstrip("\r\n")
            third_align_line = alignment_file.readline().rstrip("\r\n")

            sec_align_word = sec_align_line.split("\t")[0]
            third_align_word = third_align_line.split("\t")[0]

            file_lines.append(sec_align_line.split("\t"))
            file_lines.append(third_align_line.split("\t"))

            flag_count = 0
            print("LASTTOK=" + last_token + "***")
            print("PRELASTOK=" + penultimate_token + "***")
            while not (((third_align_word == last_token) and
                        ((penultimate_token == "naivete" and
                          sec_align_word == "navet") or
                         (penultimate_token == "naive" and
                          sec_align_word == "nave") or
                         (third_align_word == "-RRB-" and
                          (first_align_word == "\'" or first_align_word == "\"") and
                          sec_align_word == "." and
                          penultimate_token == "\"" and
                          last_token == "-RRB-") or
                         (third_align_word == "-RRB-" and
                          (sec_align_word == "\'" or sec_align_word == "\"") and
                          first_align_word == "." and
                          penultimate_token == "\"" and
                          last_token == "-RRB-") or
                         (sec_align_word == "-RRB-" and re.search(r'\)$', penultimate_token)) or
                         (sec_align_word == "\'\'" and penultimate_token == "\"") or
                         (sec_align_word == penultimate_token) or
                         (first_align_word + sec_align_word == penultimate_token))) or
                       ((sec_align_word + third_align_word == last_token) and
                        (first_align_word == penultimate_token)) or
                       (first_align_word + sec_align_word + third_align_word == last_token) or
                       (first_align_word == "\'\'" and penultimate_token == "\"" and
                        sec_align_word + third_align_word == last_token) or
                       (last_token == "ain't'." and
                        first_align_word + sec_align_word + third_align_word == "n\'t\'.") or
                       (sec_align_word + third_align_word == ".\'\'" and
                        penultimate_token == "\"" and last_token == ".") or
                       (third_align_word == (penultimate_token + last_token) and last_token == ".") or
                       (sec_align_word == "?" and last_token == "?")):

                flag_count += 1
                print("flag**" + sec_align_word + "**")
                first_align_word = sec_align_word
                sec_align_word = third_align_word
                third_align_line = alignment_file.readline()
                if not third_align_line:
                    print("Ran out!")
                    sys.exit(-1)
                if flag_count >= 300:
                    print("Too far!")
                    sys.exit(-1)
                third_align_line = third_align_line.rstrip("\r\n")

                third_align_word = third_align_line.split("\t")[0]
                file_lines.append(third_align_line.split("\t"))

            max_index = len(file_lines)
            # print file_lines
            counter = 0
            out_line = []
            punctuation = ["ROOT", "TRACE", "\"``\"", "\"\'\'\"",
                           "\"_\""]  # "\"\'\"","\"`\"",, "\"...\"" consistent with SP
            special_tokens = ["\'\'"]  # ,"-LRB-\r\n","-RRB-\r\n" are consistent with stanford parsers output
            for word in self.words:
                if max_index > counter and file_lines[counter][0] in special_tokens:
                    out_line.append([file_lines[counter][0].replace("\r\n", "")])
                    counter += 1
                    print("found special symbol" + str(counter) + file_lines[counter - 1][0])
                if word.text not in punctuation:  # Discard all punctuation marks
                    if not ((word.text == "\"not\"" and previous_word == "\"can\"" and
                             file_lines[counter - 1][0] == "cannot") or
                            (word.text == "\".\"" and re.search(r'^\"\d+\"$', previous_word) and
                             re.search(r'\d+\.$', file_lines[counter - 1][0])) or
                            (word.text == "\"-\"" and
                             previous_word.replace("\"", "") + "-" == file_lines[counter - 1][0])):

                        new_line = [word.text]
                        if word.disc_ref:
                            new_line.append(1)
                        else:
                            new_line.append(0)
                        new_line.append(word.disc_refs)
                        if (max_index > counter and
                                "\"" + file_lines[counter][0].replace("\r\n", "") + "\"" != new_line[0]):
                            # if we don't find the target
                            if not add_suffix_prefix(punctuation, word.text, file_lines[counter][0]):
                                if re.search(r'^\"d\'', word.text):
                                    parts = word.text.split("\'")
                                    out_line.append(["\"d\'\"", 0, 0])
                                    counter += 1
                                    new_line[0] = parts[1]
                                elif word.text == "\"...\"":
                                    out_line.append(["\"..\"", 0, 0])
                                    counter += 1
                                    new_line[0] = "\".\""
                                # To account for o'clock, o'brien...
                                elif (re.search(r'^\"[o,O]\'', word.text) and
                                      file_lines[counter + 1][0] == word.text.replace("\"", "").split("\'")[1]):
                                    out_line.append(["\"" + word.text.replace("\"", "").split("\'")[0] + "\'\"", 0, 0])
                                    counter += 1
                                    new_line[0] = "\"" + word.text.replace("\"", "").split("\'")[1] + "\""
                                else:
                                    new_line.append("MISMATCH!!" + new_line[0] + " " + file_lines[counter][0])
                                    print(new_line[0])
                                    print(file_lines[counter][0])
                                    print("MISMATCH")

                            # if we DID, we just put the result
                            else:
                                new_line[0] = "\"" + file_lines[counter][0] + "\""
                        out_line.append(new_line)
                        counter += 1
                    elif file_lines[counter - 1][0] == "cannot":
                        out_line[counter - 1][0] = "\"cannot\""
                        out_line[counter - 1][3] = ""
                    elif re.search(r'\d+\.$', file_lines[counter - 1][0]):
                        out_line[counter - 1][0] = "\"" + file_lines[counter - 1][0] + "\""
                        out_line[counter - 1][3] = ""
                    else:
                        out_line[counter - 1][0] = "\"" + previous_word.replace("\"", "") + "-\""
                        out_line[counter - 1][3] = ""
                previous_word = word.text
            if counter != max_index:
                out_line[counter - 1].append("INDEX\t MISMATCH")
            print_list(out_line, file_stream)

    def print_parse_structure(self, file_stream):
        """Print the parse_structure of the current sentence"""
        out_string = ""
        # Print the word indices on a line
        for word in self.words:
            out_string += str(word.rank) + ","
        out_string = out_string[:-1] + "\n"
        # Print the words on a line
        for word in self.words:
            out_string += word.text + ","
        out_string = out_string[:-1] + "\n"
        # Print POS-tags on a line
        for word in self.words:
            out_string += '\"{}\",'.format(word.pos_tag)
        out_string = out_string[:-1] + "\n"
        # Print 1 for new discourse referents (0 for old) to a line
        for word in self.words:
            if word.disc_ref:
                out_string += "1,"
            else:
                out_string += "0,"
        out_string = out_string[:-1] + "\n"
        # Print total integration costs to a line
        for word in self.words:
            out_string += str(word.disc_refs) + ","
        out_string = out_string[:-1] + "\n"
        # Add a blank line
        out_string += "\n"
        # Print dependencies headed by each word under that word
        flags = len(self.words)
        x = 0
        while flags:
            for word in self.words:
                if len(word.out_edges) == 0 and x == 0:
                    flags -= 1
                if x < len(word.out_edges):
                    out_string += "\"{}\",".format(str(word.out_edges[x]))
                    if (x + 1) >= len(word.out_edges):
                        flags -= 1
                else:
                    out_string += ","
            x += 1
            out_string = out_string[:-1] + "\n"
            # Add two blank lines
            out_string += "\n\n"
        # Write the output
        file_stream.write(out_string)

    def save_sentence_integration_cost_features(self, file_stream):
        """Print sentence-level integration cost features"""
        sum_integration_costs = 0
        max_integration_cost = 0
        for word in self.words:
            sum_integration_costs += word.disc_refs
            if word.disc_refs > max_integration_cost:
                max_integration_cost = word.disc_refs
        # Subtract 1 from the number of words because ROOT is counted as a word
        # TODO think about how TRACE and punctuation count
        avg_integration_cost = float(sum_integration_costs) / (len(self.words)-1)
        out_string = "{} {} {}\n".format(sum_integration_costs, avg_integration_cost, max_integration_cost)
        # Write the output
        file_stream.write(out_string)

    def find_traces(self):
        for word in self.words:
            # Flags are reset for each word
            direct_object_rel_flag = False
            for edge in word.out_edges:
                if edge[0] < word.rank:
                    if edge[1] == "pobj":
                        self.insert_trace(word.rank + 1, "pobj", word.rank, edge[0])
                    if edge[1] == "dobj" and not direct_object_rel_flag:
                        self.insert_trace(word.rank + 1, "dobj", word.rank, edge[0])
                        direct_object_rel_flag = True
                    if edge[1] == "rel" and not direct_object_rel_flag:
                        self.insert_trace(word.rank + 1, "rel", word.rank, edge[0])
                        direct_object_rel_flag = True
                    if edge[1] == "advmod" and not f_adv_trace_off:
                        self.insert_trace(word.rank + 1, "advmod", word.rank, edge[0])
                    if edge[1] == "ccomp":
                        self.insert_trace(word.rank + 1, "ccomp", word.rank, edge[0])
                    if edge[1] == "nsubjpass" and word.text not in past_participle_intransitive_verbs:
                        self.insert_trace(word.rank + 1, "nsubjpass", word.rank, edge[0])

    def insert_trace(self, position, relation, governor, antecedent):
        trace = Word(position, "TRACE", "trace")
        beginning_parse_structure = self.words[:position]
        rest_phrase_structure = self.words[position:]
        for element in beginning_parse_structure:
            for edge in element.in_edges:
                if edge[0] >= position:
                    edge[0] += 1
            for edge in element.out_edges:
                if edge[0] >= position:
                    edge[0] += 1
        for element in rest_phrase_structure:
            element.rank += 1
            for edge in element.in_edges:
                if edge[0] >= position:
                    edge[0] += 1
            for edge in element.out_edges:
                if edge[0] >= position:
                    edge[0] += 1
        point = beginning_parse_structure[governor].out_edges.index([antecedent, relation])
        beginning_parse_structure[governor].out_edges[point][0] = int(position)
        point = beginning_parse_structure[antecedent].in_edges.index([governor, relation])
        beginning_parse_structure[antecedent].in_edges[point] = [position, "trace"]
        trace.in_edges.append([governor, relation])
        trace.out_edges.append([antecedent, "trace"])
        result = beginning_parse_structure + [trace] + rest_phrase_structure
        self.words = result

    def calculate_integration_cost(self):
        for word in self.words:
            if word.disc_ref:
                word.disc_refs += 1
            for edge in word.out_edges:
                if edge[0] < word.rank:
                    if edge[1] != "dobj" and edge[1] != "rel":
                        for x in range(edge[0] + 1, word.rank):
                            if self.words[x].disc_ref:
                                word.disc_refs += 1
                    else:
                        # WARNING: POSSIBLE LOSS
                        word.out_edges.remove(edge)
            if word.text == "TRACE":
                self.words[word.rank - 1].disc_refs += word.disc_refs
                word.disc_refs = 0


class Word:
    def __init__(self, position, text, pos_tag):
        self.rank = position
        self.text = text
        self.pos_tag = pos_tag
        self.in_edges = []
        self.out_edges = []
        self.disc_ref = False
        self.disc_refs = 0

    def print_word(self):
        print(self.rank)
        print(self.text)
        print(self.pos_tag)
        print(self.in_edges)
        print(self.out_edges)
        print(self.disc_ref)
        print(self.disc_refs)

    def det_disc_ref(self):
        if self.pos_tag in discourse_ref_pos_tags:
            self.disc_ref = True
        if self.pos_tag in possible_aux:
            self.disc_ref = True
            for governor in self.in_edges:
                if governor[1] == "aux" or governor[1] == "auxpass":  # Discard auxiliaries
                    self.disc_ref = False
            for governor in self.out_edges:
                if governor[1] == "possessive":  # Discard genitives 's
                    self.disc_ref = False
            if self.pos_tag == 'NN' or self.pos_tag == 'NNP':
                for governor in self.in_edges:  # Discard nouns that are not the head of the noun phrase
                    if governor[1] == 'nn':
                        self.disc_ref = False
            # Discard past participle and present participle as adjuncts
            if self.pos_tag == 'VBG' or self.pos_tag == 'VBN':
                for governor in self.in_edges:
                    if governor[1] == 'amod':
                        self.disc_ref = False
            # Discard Copulae
            if self.pos_tag in verbs:
                for governor in self.in_edges:
                    if governor[1] == 'cop':
                        self.disc_ref = False


def print_list(rows, file_stream):
    line = ""
    for x in rows:
        for y in x:
            line += str(y) + "\t"
        line += "\n"
    file_stream.write(line)


def add_suffix_prefix(punctuation_marks, word_text, target):
    for x in punctuation_marks:
        if word_text.replace("\"", "") + x.replace("\"", "") == target:
            return True
        elif x.replace("\"", "") + word_text.replace("\"", "") == target:
            return True
    return False


# This returns as output a sentence, with some needed modifications,
# it can be used to process a file with "\n" delimited sentences.
# For now, it gets the sentences from a file.
def get_sentence_to_parse_stories():
    global lines
    if len(lines) > 0:
        line = lines[0]
        lines = lines[1:]
        return line
    else:
        return False


def get_sentence_to_parse(source_file):
    global auxiliary_line
    global no_words
    sentence_file_lines = []
    if auxiliary_line == "_$Finished":
        return 0, 0, 0, 0
    if len(auxiliary_line) > 1:
        # Add this to the current sentence, last word of previous iteration
        sentence, no_words = add_word_to_sentence_mary(auxiliary_line[3], "", True, 0)
        # set turn to be the one of this new sentence
        previous_turn = auxiliary_line[2]
        previous_speaker = auxiliary_line[1]
        # Say it's not the beginning
        beginning = False
        # sentence_file_lines+=["\t".join(auxiliary_line)]
        sentence_file_lines += [auxiliary_line]
        # If there was nothing in auxiliary
    else:
        # Re-initiate the sentence, the turn and say the next word is the beginning
        sentence = ""
        previous_turn = 0
        previous_speaker = 0
        beginning = True
        sentence_file_lines = []

    # Read the next word (next line of the file)
    current_line = source_file.readline()
    # Continue until a sentence boundary is found or the file ends
    while current_line:
        # Split the current line with tabs
        current_line = current_line.split("\t")
        speaker = current_line[1]
        turn = current_line[2]
        word = current_line[3]
        if not beginning and (turn != previous_turn or speaker != previous_speaker):
            auxiliary_line = current_line  # Save the last word (to be processed as part of the next sentence)
            length = len(sentence.split())
            # print sentence_file_lines
            return sentence, length, no_words, sentence_file_lines  # Return the sentence so far captured
        else:
            # Add word to the current sentence
            sentence, no_words = add_word_to_sentence_mary(word, sentence, beginning, no_words)
            previous_turn = turn
            beginning = False
            sentence_file_lines += [current_line]
        current_line = source_file.readline()
    auxiliary_line = "_$Finished"
    length = len(sentence.split(" "))
    return sentence, length, no_words, sentence_file_lines


def get_sentence_to_parse_dundee_beta(source_file):
    end_punctuation = [".", "?", "!"]
    punctuation_dundee = [",", "\"", "...", ";", "``", "'s", "'d", "n\'t"]
    special_tokens = ["\'\'", "-LRB-", "-RRB-"]
    sentence = ""
    sentence_file_lines = []
    no_words = 0  # Number of words in the sentence
    current_line = source_file.readline()  # Read the next word (next line of the file)
    while current_line:  # Continue until a sentence boundary is found or the file ends
        current_line = current_line.split("\t")  # Split the current line with tabs
        sentence_file_lines += [current_line]
        if len(current_line) > 0:
            word = current_line[0]
            if len(current_line) > 1 and word not in special_tokens:
                # This was unused when I got here; keeping it for now. -DMH
                # id_word = current_line[1]

                if word in punctuation_dundee or sentence == "":
                    sentence = sentence + word
                else:
                    sentence = sentence + " " + word
                    no_words += 1
                if word in end_punctuation or re.search(r'\d+\.$', word):
                    length = len(sentence.split(" "))
                    return sentence, length, no_words, sentence_file_lines
            else:
                if len(current_line) == 1:
                    word = current_line[0]
                    if word == "-LRB-\r\n":
                        sentence += " ("
                    if word == "-RRB-\r\n":
                        sentence += ")"
        current_line = source_file.readline()
    length = len(sentence.split(" "))
    return sentence, length, no_words, sentence_file_lines


def get_sentence_to_parse_dundee(lines):
    global dundee_line_counter
    if dundee_line_counter < len(lines):
        sentence = lines[dundee_line_counter].replace("\n", "")
        words = lines[dundee_line_counter].split()
        dundee_line_counter += 1
        return sentence, len(words), len(words)
    return False, 0, 0


def add_word_to_sentence_mary(word, sentence, begin, num_words):
    if not begin:
        if word in punctuation_corpus:
            sentence += word
        else:
            sentence += " " + word
    else:
        sentence = sentence + word
    num_words += 1
    return sentence, num_words


# Load the Stanford Parser, with nonCollapsedDependencies
def load_stanford_parser():
    global parser
    parser = Popen(PARSER_INVOCATION, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    parser.stdout.readline()


def parse_sentence(sentence, verbose=False):
    """Send a sentence to the parser and get the output"""
    global parser
    if verbose:
        print("Sentence:", sentence)
    parser.stdin.write(sentence + "\n")
    parser.stdin.flush()
    output_parser = parser.stdout.readline()
    out = output_parser
    while "####" not in out:
        out = parser.stdout.readline()
        output_parser += out
    return output_parser


def get_elements(dependency):
    """Get the elements that conform the dependency."""
    rewrite = dependency.replace("(", "|").replace(")", "|")
    rewrite = rewrite.split("|")
    relation = rewrite[0]
    elements = rewrite[1].replace(",", "").split()
    governor = elements[0].split("-")
    governor = governor[len(governor) - 1]
    dependent = elements[1].split("-")
    dependent = dependent[len(dependent) - 1]
    return relation, int(governor), int(dependent)


def separate_parse(parse_output):
    parts = parse_output.split("\n\n")
    if len(parts) > 2:
        part1 = parts[0].split("\n")
        pos_tags = part1[1]
        dependencies = parts[1]
        return pos_tags, dependencies
    elif len(parts) == 2:
        part1 = parts[0].split("\n")
        pos_tags = part1[1]
        dependencies = ""
        return pos_tags, dependencies
    else:
        return False


def mix_files(template, pre_output_file, output_file):
    lines_temp = template.readlines()
    lines_pre_output = pre_output_file.readlines()
    final_line = ""
    length_temp = len(lines_temp)
    length_pre_output = len(lines_pre_output)
    if length_temp > length_pre_output:
        max_size = length_temp
    else:
        max_size = length_pre_output
    counter = 0
    while counter < max_size:
        if counter < length_temp and counter < length_pre_output:
            output_line = lines_pre_output[counter].rstrip() + "\n"
            output_line = output_line.replace("\"", "")
            final_line += lines_temp[counter].rstrip() + "\t" + output_line
        elif counter < length_temp:
            final_line += lines_temp[counter].rstrip() + "\t\n"
        else:
            output_line = lines_pre_output[counter].rstrip() + "\n"
            output_line = output_line.replace("\"", "")
            final_line += "\t\t\t\t\t\t\t\t\t\t\t\t\t\t" + output_line
        counter += 1
    output_file.write(final_line)


def mix_files_dundee(template, pre_output_file, output_file):
    lines_temp = template.readlines()
    lines_pre_output = pre_output_file.readlines()
    final_line = ""
    length_temp = len(lines_temp)
    length_pre_output = len(lines_pre_output)
    if length_temp > length_pre_output:
        max_size = length_temp
    else:
        max_size = length_pre_output
    counter = 0
    while counter < max_size:
        if counter < length_temp and counter < length_pre_output:
            output_line = lines_pre_output[counter].rstrip() + "\n"
            output_line = output_line.replace("\"", "")
            if len(lines_temp[counter].rstrip().split("\t")) < 2:
                final_line += lines_temp[counter].rstrip() + "\t\t" + output_line
            else:
                final_line += lines_temp[counter].rstrip() + "\t" + output_line
        elif counter < length_temp:
            final_line += lines_temp[counter].rstrip() + "\t\n"
        else:
            output_line = lines_pre_output[counter].rstrip() + "\n"
            output_line = output_line.replace("\"", "")
            final_line += "\t\t" + output_line
        counter += 1
    output_file.write(final_line)


def print_usage():
    print("./integration_cost.py SENTS_FILE OUTPUT_FILE [OPTIONS]")
    print()
    print("OPTIONS:")
    print("  --with-alignments    the first option specifies an alignment file")
    print("  --advTraceOff        turn off adverbial traces")
    print("  --stories            the general mode created by Jesus")
    print("  --sentfeats          just output sentence-features")
    print("  --dundee             use the mode for Dundee data")
    print("  --verbose            print additional output to screen")


if __name__ == "__main__":
    verbose = False
    mode = None
    align_filename = None
    alignment = None
    f_adv_trace_off = False
    auxiliary_line = []
    no_words = 0

    if len(sys.argv) < 2 or "-h" in sys.argv:
        print_usage()
        exit()
    # Process arguments
    # file with the sentences
    input_filename = sys.argv[1]
    # final output filename
    output_filename = sys.argv[2]
    if len(sys.argv) > 3:
        rest_args = sys.argv[3:]
        if "--with-alignments" in rest_args:
            # "the file to which it has to be aligned the output"
            align_filename = sys.argv[3]
        if "--advTraceOff" in sys.argv[3:]:
            print("adverbial traces off!")
            f_adv_trace_off = True
        if "--stories" in sys.argv[3:]:
            print("Using Stories mode...")
            mode = "stories"
        if "--sentfeats" in sys.argv[3:]:
            print("Using sentence features mode...")
            mode = "sentence_features"
        if "--dundee" in sys.argv[3:]:
            print("Using Dundee mode...")
            print("NB: This has not been tested since 2014. Refactoring has happened since then.")
        if "--verbose" in sys.argv[3:]:
            print("Printing additional output to stdout in verbose mode.")
            verbose = True
    if not mode:
        mode = "stories"

    # Check args to see if we're using adverbial traces or not
    f_adv_trace_off = False

    # Open our input and output files
    source = open(input_filename, 'r')
    output = open(output_filename, 'w')

    if mode == "dundee_fixed":
        # We require an alignment file for Dundee, so fail and print usage if this is not provided
        if align_filename:
            alignment = open(align_filename, 'r')
        else:
            # Close open files
            source.close()
            output.close()
            # Print usage and quit
            print_usage()
            exit()

        # Intermediate file; penultimate step, used to produce final output
        intermediate_file = open(INTERMEDIATE_FILENAME, 'w')

        direct_object_rel_flag = False

        load_stanford_parser()

        lines = source.readlines()
        dundee_line_counter = 0
        line, length, numWords = get_sentence_to_parse_dundee(lines)

        line_counter = 0

        intermediate_file.write("Word\tDiscRef\tIntegrationCost\t\n")
        while line:
            print(line)
            # print(file_lines)
            if length > 1:
                if line_counter > 149:  # Reload Stanford Parser every 150 lines, to avoid broken pipes
                    parser.kill()
                    load_stanford_parser()
                    line_counter = 0
                    print("STANFORD PARSER RELOADED")
                parserOutput = parse_sentence(line, verbose)
                posTags, dependencies = separate_parse(parserOutput)
                parseStructure = ParseStructure(posTags, dependencies, verbose)
                parseStructure.find_traces()
                parseStructure.solve_coordination()
                parseStructure.set_referents()
                parseStructure.calculate_integration_cost()
                parseStructure.print_parse_structure_dundee(intermediate_file, line, alignment)
                line_counter += 1
            elif numWords < 2:
                intermediate_file.write(line + "\t0\t0\n")
            else:
                intermediate_file.write("PARSER OUTPUT LESS THAN 2\n\n")
            # line,length,numWords,fileLines=get_sentence_to_parse_dundee_beta(source)
            line, length, numWords = get_sentence_to_parse_dundee(lines)

        parser.kill()
        source.close()
        intermediate_file.close()

        # PART MODIFIED FOR DUNDEE
        source = open(align_filename)
        intermediate_file = open(INTERMEDIATE_FILENAME)
        mix_files_dundee(source, intermediate_file, output)
        source.close()
        intermediate_file.close()
        output.close()
    elif mode in ["sentence_features", "stories"]:
        if mode == "sentence_features":
            output.write("total_integration_cost avg_integration_cost max_integration_cost\n")
        lines = source.read().split('\n')

        load_stanford_parser()

        line = get_sentence_to_parse_stories()

        line_counter = 0
        while line:
            # Reload Stanford Parser every 150 lines, to avoid broken pipes.
            if line_counter == 150:
                parser.kill()
                load_stanford_parser()
                line_counter = 0
                print("STANFORD PARSER RELOADED")
            parser_output = parse_sentence(line, verbose)
            pos_tags, dependencies = separate_parse(parser_output)
            parse_structure = ParseStructure(pos_tags, dependencies, verbose)
            parse_structure.find_traces()
            parse_structure.solve_coordination()
            parse_structure.set_referents()
            parse_structure.calculate_integration_cost()

            if mode == "sentence_features":
                parse_structure.save_sentence_integration_cost_features(output)
            elif mode == "stories":
                parse_structure.print_parse_structure(output)
            line = get_sentence_to_parse_stories()
            line_counter += 1

        output.close()
    else:
        # Close open files
        source.close()
        output.close()
        print_usage()
        exit()
