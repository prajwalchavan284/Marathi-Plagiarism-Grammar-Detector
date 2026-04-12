import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from difflib import SequenceMatcher
import re
import string
import logging
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional
import unicodedata

logger = logging.getLogger(__name__)

@dataclass
class PlagiarismConfig:
    tfidf_weight: float = 0.4
    bert_weight: float = 0.6
    threshold: float = 0.55
    max_features: int = 8000
    min_df: int = 1
    max_df: float = 0.95
    ngram_range: Tuple[int, int] = (1, 3)
    batch_size: int = 16
    cache_embeddings: bool = True

class MarathiTextProcessor:
    def __init__(self):
        self.marathi_stopwords = self._load_stopwords()
        self.marathi_punctuation = string.punctuation + '।॥॰'
        self.devanagari_range = r'[\u0900-\u097F]'
        self.marathi_suffixes = ['ला', 'ने', 'चा', 'ची', 'चे', 'मधे', 'वर', 'खाली']
        self.marathi_prefixes = ['अ', 'आ', 'वि', 'दु', 'नि', 'सु']

    def _load_stopwords(self) -> set:
        base_stopwords = {
            'आणि', 'ते', 'ती', 'तो', 'त्या', 'तुमच्या', 'तुम्ही', 'मी', 'आहे', 'आहेत',
            'की', 'पण', 'म्हणून', 'होता', 'होती', 'होते', 'असून', 'किंवा', 'परंतु',
            'तर', 'मग', 'जर', 'तरी', 'काय', 'कोण', 'कसे', 'केव्हा', 'का', 'कुठे',
            'कोणते', 'फक्त', 'सगळे', 'आज', 'उद्या', 'काल', 'येथे', 'तेथे', 'सर्व',
            'अनेक', 'दोन', 'तीन', 'चार', 'पाच', 'दहा', 'शेकडो', 'हजारो', 'लाख',
            'अशी', 'असे', 'आपण', 'आपल्या', 'त्यानी', 'त्यांनी', 'तुझी', 'माझा',
            'माझी', 'माझे', 'तुझा', 'तुझे', 'त्याचा', 'त्याची', 'त्याचे', 'आमचा',
            'आमची', 'आमचे', 'त्यांचा', 'त्यांची', 'त्यांचे', 'हा', 'ही', 'हे', 'या'
        }
        extended_stopwords = {
            'अधिक', 'कमी', 'समान', 'वेगळे', 'सारखे', 'प्रत्येक', 'काही', 'सगळे',
            'सर्व', 'एक', 'दोन', 'तीन', 'चार', 'पाच', 'सहा', 'सात', 'आठ', 'नऊ', 'दहा',
            'माझ्या', 'तुझ्या', 'त्याच्या', 'तिच्या', 'त्यांच्या', 'आमच्या', 'तुमच्या',
            'या', 'ता', 'ना', 'स', 'ल', 'च', 'शी', 'साठी', 'बद्दल', 'विषयी'
        }
        return base_stopwords.union(extended_stopwords)

    def normalize_text(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        text = unicodedata.normalize('NFC', text)
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'\d{10,}', '', text)
        text = re.sub(r'[०-९]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'([।])\1+', r'\1', text)
        return text.strip()

    def tokenize_marathi(self, text: str) -> List[str]:
        tokens = re.findall(r'\w+', text, re.UNICODE)
        filtered_tokens = [
            token for token in tokens
            if len(token) > 1 and re.search(self.devanagari_range, token)
        ]
        return filtered_tokens

    def preprocess_text(self, text: str) -> str:
        text = self.normalize_text(text)
        text = text.translate(str.maketrans('', '', self.marathi_punctuation))
        tokens = self.tokenize_marathi(text)
        tokens = [token for token in tokens if token not in self.marathi_stopwords]
        return ' '.join(tokens)

class EnhancedSimilarityCalculator:
    def __init__(self, config: PlagiarismConfig):
        self.config = config
        self.text_processor = MarathiTextProcessor()
        self.text_processor = MarathiTextProcessor()
        # Vectorizer will be instantiated locally per request to handle different corpus sizes
        try:
            available_models = [
                'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                'sentence-transformers/distiluse-base-multilingual-cased-v1'
            ]
            self.bert_model = None
            for model_name in available_models:
                try:
                    self.bert_model = SentenceTransformer(model_name)
                    logger.info(f"Loaded BERT model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load {model_name}: {e}")
            if self.bert_model is None:
                raise Exception("All BERT models failed to load")
        except Exception as e:
            logger.error(f"Failed to load BERT model: {e}")
            self.bert_model = None
        self.embedding_cache = {}

    def calculate_tfidf_similarity_batch(self, queries: List[str], corpus_docs: List[str]) -> np.ndarray:
        try:
            processed_corpus = [self.text_processor.preprocess_text(doc) for doc in corpus_docs]

            custom_max_df = 1.0 if len(corpus_docs) < 10 else self.config.max_df

            local_vectorizer = TfidfVectorizer(
                max_features=self.config.max_features,
                min_df=1,
                max_df=custom_max_df,
                ngram_range=self.config.ngram_range,
                tokenizer=self.text_processor.tokenize_marathi,
                lowercase=True,
                strip_accents='unicode',
                token_pattern=r'\w+'
            )

            corpus_tfidf = local_vectorizer.fit_transform(processed_corpus)
            similarities = []
            for i in range(0, len(queries), self.config.batch_size):
                batch_queries = queries[i:i + self.config.batch_size]
                processed_queries = [self.text_processor.preprocess_text(q) for q in batch_queries]
                query_tfidf = local_vectorizer.transform(processed_queries)
                batch_similarities = cosine_similarity(query_tfidf, corpus_tfidf)
                similarities.extend(batch_similarities)
            return np.array(similarities)
        except Exception as e:
            logger.error(f"Error in TF-IDF calculation: {e}")
            return np.zeros((len(queries), len(corpus_docs)))

    def calculate_bert_similarity_batch(self, queries: List[str], corpus_docs: List[str]) -> np.ndarray:
        try:
            if self.bert_model is None:
                return np.zeros((len(queries), len(corpus_docs)))
            corpus_key = hash(tuple(corpus_docs))
            if self.config.cache_embeddings and corpus_key in self.embedding_cache:
                corpus_embeddings = self.embedding_cache[corpus_key]
            else:
                corpus_embeddings = self.bert_model.encode(corpus_docs, convert_to_tensor=True, show_progress_bar=False, batch_size=self.config.batch_size)
                if self.config.cache_embeddings:
                    self.embedding_cache[corpus_key] = corpus_embeddings
            query_embeddings = self.bert_model.encode(queries, convert_to_tensor=True, show_progress_bar=False, batch_size=self.config.batch_size)
            similarities = cosine_similarity(query_embeddings.cpu().numpy(), corpus_embeddings.cpu().numpy())
            return similarities
        except Exception as e:
            logger.error(f"Error in BERT calculation: {e}")
            return np.zeros((len(queries), len(corpus_docs)))

class EnhancedMarathiPlagiarismDetector:
    def __init__(self, config: Optional[PlagiarismConfig] = None):
        self.config = config or PlagiarismConfig()
        self.similarity_calculator = EnhancedSimilarityCalculator(self.config)
        self.corpus = []
        self.corpus_metadata = []
        self._initialize_default_corpus()

    def _initialize_default_corpus(self):
        default_docs = [
            """जॉर्जला नीओशोत पोहोचायला रात्र झाली. एका पडक्या गोठ्यात त्याने आपलं चालून चालून थकलेलं दुबळं शरीर आडवं केलं. पहाटेच उठला. आपल्या शेजारी कोण म्हणून पाहतो तो एक भला दांडगा कुत्रा ! बापरे !! रात्र याच्या संगतीत गेली तर !!
त्या सकाळी आयुष्यात प्रथमच त्याने शाळेत पाऊल टाकलं. सारी निग्रोच मुलं होती. जॉर्जचं ते गबाळं ध्यान, डोक्यावर गोठ्यातल्या गवताची चिकटलेली तुसं आणि त्याचा तो चिरका आवाज ! अडखळत बोलणं! सारी मुलं त्याच्याकडे विचित्र नजरेने पाहत होती.""",
            """शेती हा भारतातील प्रमुख व्यवसाय आहे. पावसावर अवलंबून असलेल्या शेतीला सध्या अनेक समस्या आहेत. शेतकऱ्यांना पिकांच्या योग्य किमत मिळत नाहीत आणि त्यामुळे त्यांचे आर्थिक स्थिती बिघडते."""
        ]
        self.build_corpus(default_docs, ["Doc_1_George", "Doc_2_Agriculture"])

    def build_corpus(self, documents: List[str], document_names: Optional[List[str]] = None):
        if not documents:
            return
        self.corpus = documents
        self.corpus_metadata = [{'name': name} for name in document_names] if document_names else [{'name': f"Doc_{i}"} for i in range(len(documents))]

    def detect_plagiarism_single(self, query_text: str) -> Dict[str, Any]:
        if not self.corpus or not query_text:
            return {"error": "Invalid query or corpus"}

        tfidf_sim = self.similarity_calculator.calculate_tfidf_similarity_batch([query_text], self.corpus)[0]
        bert_sim = self.similarity_calculator.calculate_bert_similarity_batch([query_text], self.corpus)[0]

        ensemble_sim = (self.config.tfidf_weight * tfidf_sim) + (self.config.bert_weight * bert_sim)

        max_similarity = float(np.max(ensemble_sim))
        max_index = int(np.argmax(ensemble_sim))
        threshold = self.config.threshold

        details = []
        for i, score in enumerate(ensemble_sim):
            details.append({
                'document_name': self.corpus_metadata[i]['name'],
                'similarity': float(np.round(score * 100, 2)),
                'is_plagiarized': bool(score >= threshold)
            })

        details.sort(key=lambda x: x['similarity'], reverse=True)

        return {
            'is_plagiarized': bool(max_similarity >= threshold),
            'max_similarity': float(np.round(max_similarity * 100, 2)),
            'matched_document': self.corpus_metadata[max_index]['name'] if bool(max_similarity >= threshold) else None,
            'detailed_results': details
        }

    def _split_sentences(self, text: str) -> List[str]:
        """Split Marathi/Hindi text into sentences on punctuation boundaries."""
        parts = re.split(r'[.\u0964\u0965\n]', text)
        return [s.strip() for s in parts if s.strip() and len(s.strip()) > 5]

    def detect_plagiarism_custom(self, query_text: str, reference_text: str) -> Dict[str, Any]:
        if not reference_text or not query_text:
            return {"error": "Invalid query or reference text"}

        logger.info(f"Custom comparison | query_len={len(query_text)} ref_len={len(reference_text)}")

        # Fast shortcut: identical texts
        if query_text.strip() == reference_text.strip():
            return {
                'is_plagiarized': True,
                'max_similarity': 100.0,
                'matched_document': 'Uploaded Reference Text',
                'matched_sentence': query_text.strip(),
                'detailed_results': [{'document_name': 'Uploaded Reference Text', 'similarity': 100.0, 'is_plagiarized': True}]
            }

        threshold = self.config.threshold

        # Split BOTH into sentences for granular matching
        ref_sentences = self._split_sentences(reference_text)
        query_sentences = self._split_sentences(query_text)

        # Fallback: treat entire texts as single unit
        if not ref_sentences:
            ref_sentences = [reference_text]
        if not query_sentences:
            query_sentences = [query_text]

        logger.info(f"Sentences: query={len(query_sentences)} ref={len(ref_sentences)}")

        best_score = 0.0
        best_ref_sent = ''
        sentence_results = []

        for q in query_sentences:
            for r in ref_sentences:
                # Character-level sequence match
                seq = SequenceMatcher(None, q, r).ratio()

                # Run TF-IDF + BERT only for plausible pairs
                if seq > 0.1:
                    tfidf = float(self.similarity_calculator.calculate_tfidf_similarity_batch([q], [r])[0][0])
                    bert = float(self.similarity_calculator.calculate_bert_similarity_batch([q], [r])[0][0])
                else:
                    tfidf, bert = 0.0, 0.0

                # Weighted blend: 40% seq (exact match), 30% tfidf, 30% bert
                score = float(np.clip(0.4 * seq + 0.3 * tfidf + 0.3 * bert, 0.0, 1.0))

                sentence_results.append({
                    'query_sentence': q[:100],
                    'ref_sentence': r[:100],
                    'similarity': round(score * 100, 2),
                    'is_plagiarized': bool(score >= threshold)
                })

                if score > best_score:
                    best_score = score
                    best_ref_sent = r

        sentence_results.sort(key=lambda x: x['similarity'], reverse=True)

        return {
            'is_plagiarized': bool(best_score >= threshold),
            'max_similarity': round(best_score * 100, 2),
            'matched_document': 'Uploaded Reference Text' if best_score >= threshold else None,
            'matched_sentence': best_ref_sent,
            'detailed_results': [{
                'document_name': 'Uploaded Reference Text',
                'similarity': round(best_score * 100, 2),
                'is_plagiarized': bool(best_score >= threshold)
            }],
            'sentence_matches': sentence_results[:10]
        }

# Global instance for easier API use
plagiarism_detector = EnhancedMarathiPlagiarismDetector()
