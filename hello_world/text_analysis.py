import collections
import copy
from typing import List, Tuple
import spacy
from icecream import ic
from spacy.matcher import PhraseMatcher, Matcher
from spacy.tokens.span import Span


class TextAnalysis:
    # a filter for matches aka stage 1 of filtering phrases this threshold determines what we are allowing to pass to
    # the second stage. (lower number means more results that probably won't make it to the finals stage therefore
    # just a waste of resources/computing time)
    _threshold_1 = 0.9

    # filter for sentence itself aka stage 2 of filtering.
    # this threshold is actually determines what we are allowing as a result.
    _threshold_2 = 0.94

    # steps for trying to optimize a match.
    # the number value is a sweet spot for steps to take and reevaluate it's score
    _steps = 5

    # if length is smaller than 3 words no don't try to optimize it.
    _cancel_opt = 3

    def __init__(self, text: str, tracker: list):
        """
        :param text: text to search within
        :param tracker: values to search
        """
        self.nlp = spacy.load("en_core_web_md")
        self.text: str = text
        self.doc = self.nlp(text)
        self.tracker = [t.lower() for t in tracker]

    @staticmethod
    def _generate_pattern(term: Span) -> list:
        """
        generate a pattern to find matches for the term.
        :param term: the term to generate pattern for
        :return: the pattern generated
        """
        pattern = []
        for i, token in enumerate(term):
            size = len(term)

            if not token.is_punct:
                pattern.append({"LEMMA": str(token.text), "OP": "?"})

                # add {} only if not last one
                if i < size - 1:
                    pattern.append({})

        return pattern

    def _get_matches(self, search_term: Span) -> list:
        """
        get matches for similarity phrases the matches are not exact match
        but instead a match that has a high potential
        :param search_term: the term for our match
        :return: matches list
        """
        pattern = self._generate_pattern(search_term)
        matcher = Matcher(self.nlp.vocab)
        matcher.add("match", [pattern])
        matches = matcher(self.doc)
        return matches

    def _similarity_check(self, text: str) -> list:
        """
        checks for phrases that are similar to the text provided
        :param text: text to check similarities for
        :return: list of tuple that contains spans and score for all the sentences that are similar to text
        """
        search_terms = self.nlp(text)
        matches = self._get_matches(search_terms)

        # widening the range of the phrases that might be a match by few words.
        search_len = len(search_terms)
        param_for_match_len_shortest = (search_len - 1) if search_len <= 1 else search_len
        param_for_match_len_longest = search_len + 2

        # takes all the matches that maybe be a good fit in terms of their length. matches that are too long or too
        # short won't appear. example if we search "how are you?" than any match that is 3X times the length of this
        # phrase is probably not a good match, same goes for much smaller phrases than what the user searched.
        matches_that_might_fit = [self.doc[start:end] for _, start, end in matches if
                                  param_for_match_len_shortest <= end - start <= param_for_match_len_longest]

        fit = self._filter_matches(matches_that_might_fit, search_terms)
        return fit

    def _filter_matches(self, matches_that_might_fit: list, search_term) -> List[tuple]:
        """
        this function is second stage of filtering.
        tries to improve sentences similarity score by narrowing down or widening them.

        any sentence that has similarity score bigger than:
        _threshold_1 and _threshold_2 are similar to the search term

        :param matches_that_might_fit:
        :param search_term:
        :return: similar sentences list
        """
        fit: List[Tuple] = []
        for match in matches_that_might_fit:
            # Filtering matches based on similarity
            if match.similarity(search_term) > self._threshold_1:
                start, end, _ = self._opt_by_widening(match, search_term)
                start, end, similarity_score = self._opt_by_narrowing(self.doc[start:end], search_term)
                if similarity_score > self._threshold_2:
                    fit.append((self.doc[start:end], similarity_score, search_term))

        fit.sort(key=lambda x: x[1])
        return fit

    def _get_exact_match(self) -> list:
        """
        finding exact matches.
        :return: list of except matches
        """
        matcher = PhraseMatcher(self.nlp.vocab)
        patterns = [self.nlp.make_doc(text) for text in self.tracker]

        matcher.add("match", patterns)
        matches = matcher(self.doc)

        return [self.doc[start:end] for _, start, end, in matches]

    def analyze_and_get_response(self) -> List[dict]:
        """
        analyze the text and search for exact or similar matches to the tracker values.
        :return: returns dict with data about matches and similar matches.
        """
        exact_matches_list = self._get_exact_match()

        similarity_matches_list = []
        for text in self.tracker:
            for res in self._similarity_check(text):
                similarity_matches_list.append(res)

        # checks there isn't overlapping between exact matches and similarities
        instances_found = self._remove_overlaps(exact_matches_list, similarity_matches_list)
        return self._get_matches_metadata(instances_found)

    def _opt_by_widening(self, span: Span, search_term: Span) -> tuple:
        """
        tries to optimize the sentence similarity score by making it larger
        :param span: the span.
        :param search_term: the term we would like to search.
        :return:if it's similarity score isn't improved than returns the original sentence otherwise returns new sentence
        """
        start = span.start
        end = span.end
        original_value = span.similarity(search_term)

        for i in range(5):
            if start - 1 > 0 and self.doc[start - 1: end].similarity(search_term) > original_value \
                    and self.doc[start - 1: start].text not in ['.', ',']:
                start -= 1

        for i in range(5):
            if end + 1 < len(self.doc) and self.doc[start: end + 1].similarity(search_term) > original_value:
                end += 1

        return start, end, self.doc[start:end].similarity(search_term)

    def _opt_by_narrowing(self, span: Span, search_term: Span) -> tuple:
        """
        tries to optimize the sentence similarity score by making it smaller
        :param span: the span.
        :param search_term: the term we would like to search.
        :return:if it's similarity score isn't improved than returns the original sentence otherwise returns new sentence
        """

        # if span is smaller than _cancel_opt value than don't try to optimize.
        if len(span) <= self._cancel_opt:
            return span.start, span.end, self.doc[span.start:span.end].similarity(search_term)

        original_start = start = span.start
        original_end = end = span.end
        original_value = span.similarity(search_term)

        # sometimes some spans has no vector therefore it's similarity will raise ZeroDivisionError,
        # if so just return the original span and don't try to optimize it's score.
        try:
            # loops through the span, if finds dot at the middle cuts sentence to half and compare each half
            for token in span:
                if token.text == '.' and token.i != end:
                    span1 = self.doc[start:token.i]
                    span2 = self.doc[token.i:end]
                    if span1.similarity(search_term) > span2.similarity(search_term):
                        end = token.i
                    else:
                        start = token.i

            # tries to make span smaller by advancing it's start towards the end.
            # if the score is better than we have a better match.
            counter = start
            for i in range(self._steps):
                if start + 1 < len(self.doc) and \
                        (counter + 1) != end and counter < end - 1 and \
                        self.doc[counter + 1: end].similarity(search_term) > original_value:
                    start = counter
                counter += 1

            # tries to make span smaller by advancing it's end towards the start.
            # if the score is better than we have a better match.
            counter = end
            for i in range(self._steps):
                if end - 1 > start and counter - 1 > start and self.doc[start: counter - 1].similarity(
                        search_term) > original_value:
                    end = counter
                counter -= 1

            # if narrowing down won't give better results return original sentence.
            if original_value > self.doc[start:end].similarity(search_term):
                return original_start, original_end, original_value

        except ZeroDivisionError:
            return original_start, original_end, original_value

        # returns a new span with better similarity score
        return start, end, self.doc[start:end].similarity(search_term)

    def _remove_overlaps(self, exact_matches_list: list, similarity_matches_list: list) -> list:
        """
        removes overlaps between 2 lists.

        example: search term is : "hi how are"
                entire phrase is : how are you today sir?
                exact match is : how are you
                similar match is : how are you sir

        exact and similar are overlapping so will delete similar in this case.

        :param exact_matches_list:  list of exact matches
        :param similarity_matches_list:  list of similar matches
        :return: return list with no overlaps btween results.
        """
        similarity_matches_list_copy = copy.copy(similarity_matches_list)
        # goes over  lists and removes overlaps if similarities lapping with exact-matches removes the similarities.
        for sim_matches in similarity_matches_list:
            span: Span = sim_matches[0]
            start = span.start
            end = span.end

            for exact_match in exact_matches_list:
                if (start <= exact_match.start and end >= exact_match.end) or \
                        (start < exact_match.start < end < exact_match.end) or \
                        (exact_match.start < start < exact_match.end < end):
                    similarity_matches_list_copy.remove(sim_matches)

        # ic(similarity_matches_list_copy)
        no_overlap_similarity = self._del_same_list_overlaps(similarity_matches_list_copy)

        # extract only the span and search term (don't need the similarity score anymore)
        similarity_match = [(match[0], match[2]) for match in no_overlap_similarity]
        exact_match = [(match, match) for match in exact_matches_list]

        return exact_match + similarity_match

    @staticmethod
    def _del_same_list_overlaps(s_list: list) -> list:
        """
        deletes overlaps for the same list.

        :param s_list: list to remove overlaps from.
        :return: list with no overlaps
        """
        copy1 = copy.copy(s_list)
        copy2 = copy.copy(s_list)

        for sim in copy1:
            sim_span = sim[0]
            sim_score = sim[1]
            for s in copy2:
                # skips if it is same span
                if not (sim_span.start == s[0].start and sim_span.end == s[0].end):

                    if sim_span.start <= s[0].start <= sim_span.end or \
                            s[0].start <= sim_span.start <= s[0].end or \
                            sim_span.start <= s[0].start and sim_span.end >= s[0].end:

                        try:
                            if sim_score > s[1]:
                                copy1.remove(s)
                            else:
                                copy1.remove(sim)
                        except Exception as e:
                            pass
                            # ic(e)
        return copy1

    def _get_matches_metadata(self, match_spans_list: list) -> List[dict]:
        """
        finds what sentence id the match is from

        :param match_spans_list: lists of spans that are match
        :return: list of dict of all the matches that found
        """

        # creating a list of sentences and adding "id" attr to each sentence in the doc.
        # (the id is not given with spacy)
        sentences_list: List[dict] = []
        for i, sentence in enumerate(self.doc.sents):
            sentences_list.append({"sentence_id": i,
                                   "sentence": sentence,
                                   "sentence_start": sentence.start,
                                   "sentence_end": sentence.end})

        # looping through each match and sentence checking if this is our match. if so adding it to the result and
        # calculating the start-word and end-word of each match relative to the sentence and not the doc.

        list_of_results: List[dict] = []
        for tuple_result in match_spans_list:
            match_span = tuple_result[0]

            for sentence in sentences_list:
                if sentence['sentence_start'] <= match_span.start and match_span.end <= sentence['sentence_end']:
                    result = collections.OrderedDict()
                    result["sentence_idx"] = sentence["sentence_id"]
                    result["start_word_idx"] = match_span.start - sentence['sentence_start']
                    result["end_word_idx"] = match_span.end - sentence['sentence_start'] - 1
                    result["tracker_value"] = tuple_result[1].text
                    result["transcribe_value"] = match_span.text

                    list_of_results.append(result)
                    break

        list_of_results.sort(key=lambda x: x["sentence_idx"])
        return self._remove_duplicates(list_of_results)

    @staticmethod
    def _remove_duplicates(list_dup: list) -> List[dict]:
        dict_to_return = dict()
        for item in list_dup:
            dict_to_return[item.get("transcribe_value") +
                           str(item.get("sentence_idx")) +
                           str(item.get("start_word_idx")) +
                           str(item.get("end_word_idx"))] = item

        return [dict_to_return[key] for key in dict_to_return.keys()]
