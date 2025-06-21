"""
Enhanced Document Retriever for Complex Queries

This module provides advanced search capabilities that can handle complex questions
without relying on hardcoded phrases, specifically optimized for English queries.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class SearchTerm:
    """Represents a search term with metadata."""
    term: str
    weight: float
    category: str  # 'concept', 'action', 'entity', 'modifier'
    synonyms: List[str]


@dataclass
class ChunkMatch:
    """Represents a matched document chunk with scoring."""
    chunk_id: str
    text: str
    score: float
    matched_terms: List[str]
    chunk_type: str
    start_char: int
    end_char: int
    document_info: Dict[str, Any]


class EnhancedDocumentRetriever:
    """Advanced document retriever optimized for complex English queries."""
    
    def __init__(self):
        # Enhanced synonym dictionary for legal and technical terms
        self.concept_synonyms = {
            # Legal concepts
            'accept': ['agree', 'consent', 'approve', 'acknowledge', 'embrace', 'adopt'],
            'acceptance': ['agreement', 'consent', 'approval', 'acknowledgment', 'adoption'],
            'responsibility': ['obligation', 'duty', 'liability', 'accountability', 'commitment'],
            'obligations': ['duties', 'responsibilities', 'commitments', 'requirements', 'mandates'],
            'rights': ['privileges', 'entitlements', 'permissions', 'authorities', 'powers'],
            'license': ['permit', 'authorization', 'permission', 'grant', 'allow'],
            'licensed': ['permitted', 'authorized', 'allowed', 'granted', 'entitled'],
            'distribute': ['provide', 'share', 'disseminate', 'deliver', 'supply'],
            'distribution': ['sharing', 'dissemination', 'delivery', 'provision', 'supply'],
            'redistribute': ['reshare', 'redisseminate', 'redelivery', 'resupply'],
            'modification': ['change', 'alteration', 'amendment', 'update', 'revision'],
            'modifications': ['changes', 'alterations', 'amendments', 'updates', 'revisions'],
            'sublicense': ['sublicensing', 'sub-license', 'relicense', 'secondary license'],
            'requirements': ['conditions', 'obligations', 'mandates', 'specifications', 'criteria'],
            'comply': ['adhere', 'conform', 'observe', 'follow', 'satisfy'],
            'compliance': ['adherence', 'conformity', 'observance', 'satisfaction'],
            'noncompliance': ['violation', 'breach', 'non-adherence', 'non-conformity'],
            'cure': ['fix', 'remedy', 'correct', 'resolve', 'address'],
            'terminate': ['end', 'cancel', 'discontinue', 'cease', 'stop'],
            'termination': ['ending', 'cancellation', 'discontinuation', 'cessation'],
            'governing': ['controlling', 'ruling', 'applicable', 'relevant'],
            'warranty': ['guarantee', 'assurance', 'promise', 'commitment'],
            'indemnity': ['protection', 'compensation', 'reimbursement', 'coverage'],
            'export': ['international', 'foreign', 'overseas', 'external'],
            'endorsement': ['approval', 'support', 'backing', 'recommendation'],
            'commercial': ['business', 'trade', 'market', 'profit'],
            'advantage': ['benefit', 'edge', 'superiority', 'gain'],
            'registration': ['enrollment', 'signup', 'recording', 'listing'],
            'representations': ['statements', 'declarations', 'assertions', 'claims'],
            'purpose': ['objective', 'goal', 'aim', 'intention', 'reason'],
            'subject': ['covered', 'relevant', 'applicable', 'related'],
            'contributor': ['provider', 'supplier', 'giver', 'author'],
            'recipient': ['receiver', 'user', 'beneficiary', 'party'],
            'agency': ['organization', 'department', 'bureau', 'authority'],
            'government': ['federal', 'state', 'public', 'official'],
            
            # Actions and verbs
            'trigger': ['cause', 'initiate', 'activate', 'start', 'prompt'],
            'perform': ['execute', 'carry out', 'conduct', 'do', 'implement'],
            'activities': ['actions', 'operations', 'tasks', 'work', 'processes'],
            'define': ['specify', 'describe', 'explain', 'clarify', 'identify'],
            'provide': ['supply', 'give', 'offer', 'furnish', 'deliver'],
            'include': ['contain', 'comprise', 'incorporate', 'encompass'],
            'remove': ['delete', 'eliminate', 'take away', 'extract'],
            'request': ['ask for', 'seek', 'require', 'demand'],
            'offer': ['provide', 'give', 'supply', 'present'],
            'fail': ['not succeed', 'be unable', 'neglect', 'omit'],
            
            # Legal entities and roles
            'recipient': ['user', 'licensee', 'party', 'entity'],
            'contributors': ['providers', 'suppliers', 'authors', 'creators'],
            'parties': ['entities', 'organizations', 'participants'],
            
            # Technical terms
            'software': ['code', 'program', 'application', 'system'],
            'source code': ['source', 'code', 'programming code'],
            'copyright': ['intellectual property', 'authorship', 'ownership'],
            'notice': ['notification', 'announcement', 'statement', 'message'],
            'patent': ['intellectual property', 'invention', 'IP'],
            
            # Time and conditions
            'when': ['if', 'upon', 'during', 'while', 'as'],
            'conditions': ['circumstances', 'situations', 'requirements', 'terms'],
            'happens': ['occurs', 'takes place', 'arises', 'comes about'],
            'stated': ['mentioned', 'specified', 'declared', 'indicated'],
            'limitations': ['restrictions', 'constraints', 'bounds', 'limits'],
            'placed': ['imposed', 'applied', 'set', 'established'],
        }
        
        # Stop words for filtering
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'must', 'this', 'that', 'these', 
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the query to extract intent, key concepts, and search terms."""
        query_lower = query.lower().strip()
        
        # Detect question type and intent
        intent = self._detect_intent(query_lower)
        
        # Extract key concepts and terms
        key_terms = self._extract_key_terms(query_lower)
        
        # Generate search variations
        search_terms = self._generate_search_terms(key_terms, intent)
        
        # Identify important phrases
        phrases = self._extract_phrases(query_lower)
        
        return {
            'original_query': query,
            'intent': intent,
            'key_terms': key_terms,
            'search_terms': search_terms,
            'phrases': phrases,
            'question_type': self._classify_question_type(query_lower)
        }
    
    def _detect_intent(self, query: str) -> Dict[str, Any]:
        """Detect the intent and focus of the query."""
        intent = {
            'type': 'general',
            'focus': [],
            'action': None,
            'entity': None
        }
        
        # Check for question words
        if any(word in query for word in ['what are', 'what is']):
            intent['type'] = 'definition'
        elif any(word in query for word in ['when', 'under what', 'if']):
            intent['type'] = 'conditions'
        elif any(word in query for word in ['how', 'what activities', 'what actions']):
            intent['type'] = 'process'
        elif any(word in query for word in ['can', 'may', 'able to']):
            intent['type'] = 'permission'
        elif 'define' in query:
            intent['type'] = 'definition'
        elif 'requirements' in query or 'must' in query or 'shall' in query:
            intent['type'] = 'obligation'
        elif 'what happens' in query or 'what is the' in query:
            intent['type'] = 'consequence'
        
        # Extract focus areas
        legal_focuses = ['patent', 'copyright', 'license', 'agreement', 'contract', 
                        'modification', 'distribution', 'sublicense', 'warranty',
                        'indemnity', 'compliance', 'termination', 'export']
        
        for focus in legal_focuses:
            if focus in query:
                intent['focus'].append(focus)
        
        return intent
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from the query."""
        # Remove punctuation and split
        cleaned_query = re.sub(r'[^\w\s]', ' ', query)
        words = cleaned_query.split()
        
        # Filter out stop words and short words
        meaningful_words = [
            word for word in words 
            if word not in self.stop_words and len(word) > 2
        ]
        
        # Add important bigrams and trigrams
        phrases = []
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i + 1]}"
            if any(important in bigram for important in 
                  ['source code', 'subject software', 'government agency', 
                   'patent rights', 'copyright notice', 'open source']):
                phrases.append(bigram)
        
        return meaningful_words + phrases
    
    def _generate_search_terms(self, key_terms: List[str], intent: Dict[str, Any]) -> List[SearchTerm]:
        """Generate weighted search terms with synonyms."""
        search_terms = []
        
        for term in key_terms:
            term_lower = term.lower()
            
            # Determine weight based on term importance
            weight = 1.0
            if term_lower in ['contributor', 'recipient', 'software', 'modification', 'license']:
                weight = 2.0
            elif term_lower in intent.get('focus', []):
                weight = 1.8
            elif len(term) > 8:  # Longer terms are often more specific
                weight = 1.5
            
            # Get synonyms
            synonyms = self.concept_synonyms.get(term_lower, [])
            
            # Determine category
            category = self._categorize_term(term_lower)
            
            search_terms.append(SearchTerm(
                term=term,
                weight=weight,
                category=category,
                synonyms=synonyms
            ))
        
        return search_terms
    
    def _categorize_term(self, term: str) -> str:
        """Categorize a term by its type."""
        concepts = ['responsibility', 'obligation', 'rights', 'license', 'agreement']
        actions = ['accept', 'distribute', 'modify', 'sublicense', 'terminate']
        entities = ['contributor', 'recipient', 'software', 'agency', 'government']
        modifiers = ['commercial', 'export', 'patent', 'copyright']
        
        if term in concepts:
            return 'concept'
        elif term in actions:
            return 'action'
        elif term in entities:
            return 'entity'
        elif term in modifiers:
            return 'modifier'
        else:
            return 'general'
    
    def _extract_phrases(self, query: str) -> List[str]:
        """Extract important phrases from the query."""
        phrases = []
        
        # Look for quoted phrases
        quoted_phrases = re.findall(r'"([^"]*)"', query)
        phrases.extend(quoted_phrases)
        
        # Look for important compound terms
        compound_patterns = [
            r'subject software',
            r'source code',
            r'government agency',
            r'patent rights',
            r'copyright notice',
            r'open source',
            r'user registration',
            r'commercial advantage',
            r'export license',
            r'governing law'
        ]
        
        for pattern in compound_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                phrases.append(pattern)
        
        return phrases
    
    def _classify_question_type(self, query: str) -> str:
        """Classify the type of question being asked."""
        if any(word in query for word in ['what are', 'define', 'definition']):
            return 'definition'
        elif any(word in query for word in ['when', 'under what conditions']):
            return 'conditional'
        elif any(word in query for word in ['can', 'may', 'able to']):
            return 'capability'
        elif any(word in query for word in ['what happens', 'consequences']):
            return 'outcome'
        elif any(word in query for word in ['how', 'what activities']):
            return 'procedural'
        elif any(word in query for word in ['requirements', 'must', 'shall']):
            return 'mandatory'
        else:
            return 'general'
    
    def create_search_patterns(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create multiple search patterns based on query analysis."""
        patterns = []
        
        search_terms = analysis['search_terms']
        phrases = analysis['phrases']
        intent = analysis['intent']
        
        # Pattern 1: Exact phrase matching (highest priority)
        if phrases:
            for phrase in phrases:
                patterns.append({
                    'type': 'exact_phrase',
                    'pattern': phrase,
                    'weight': 3.0,
                    'description': f'Exact phrase: "{phrase}"'
                })
        
        # Pattern 2: Core concept matching
        core_terms = [t for t in search_terms if t.weight >= 1.5]
        if core_terms:
            patterns.append({
                'type': 'core_concepts',
                'pattern': [t.term for t in core_terms],
                'weight': 2.5,
                'description': f'Core concepts: {[t.term for t in core_terms]}'
            })
        
        # Pattern 3: Synonym expansion
        for term in search_terms:
            if term.synonyms:
                patterns.append({
                    'type': 'synonym_expansion',
                    'pattern': [term.term] + term.synonyms,
                    'weight': 2.0,
                    'description': f'Synonyms for: {term.term}'
                })
        
        # Pattern 4: Intent-based patterns
        if intent['type'] != 'general':
            patterns.append({
                'type': 'intent_based',
                'pattern': self._get_intent_keywords(intent['type']),
                'weight': 1.8,
                'description': f'Intent: {intent["type"]}'
            })
        
        # Pattern 5: Broad keyword matching
        all_terms = [t.term for t in search_terms]
        if all_terms:
            patterns.append({
                'type': 'broad_keywords',
                'pattern': all_terms,
                'weight': 1.0,
                'description': f'Broad keywords: {all_terms[:5]}'
            })
        
        return sorted(patterns, key=lambda x: x['weight'], reverse=True)
    
    def _get_intent_keywords(self, intent_type: str) -> List[str]:
        """Get keywords associated with specific intent types."""
        intent_keywords = {
            'definition': ['define', 'definition', 'means', 'refers to', 'is defined as', 'the term'],
            'conditions': ['if', 'when', 'upon', 'where', 'provided that', 'subject to', 'conditions', 'requirements'],
            'permission': ['may', 'can', 'permitted to', 'authorized to', 'licensed to', 'right to'],
            'obligation': ['shall', 'must', 'will', 'required to', 'obligated to', 'responsibility', 'duty'],
            'consequence': ['result in', 'lead to', 'cause', 'trigger', 'penalty', 'consequence', 'happens']
        }
        return intent_keywords.get(intent_type, [])
    
    def search_text(self, text: str, analysis: Dict[str, Any]) -> List[ChunkMatch]:
        """Search text using the analyzed query."""
        patterns = self.create_search_patterns(analysis)
        chunks = self._split_text_into_chunks(text)
        
        matches = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_matches = self._score_chunk_against_patterns(chunk_text, patterns, chunk_idx)
            matches.extend(chunk_matches)
        
        # Sort by score and return top matches
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:10]  # Return top 10 matches
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into searchable chunks."""
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _score_chunk_against_patterns(self, chunk_text: str, patterns: List[Dict[str, Any]], 
                                    chunk_idx: int) -> List[ChunkMatch]:
        """Score a chunk against all search patterns."""
        chunk_lower = chunk_text.lower()
        total_score = 0
        matched_terms = []
        
        for pattern in patterns:
            pattern_data = pattern['pattern']
            pattern_weight = pattern['weight']
            pattern_type = pattern['type']
            
            if pattern_type == 'exact_phrase':
                if pattern_data.lower() in chunk_lower:
                    total_score += pattern_weight * 10  # High score for exact phrases
                    matched_terms.append(pattern_data)
            
            elif pattern_type == 'core_concepts':
                # Check if all core concepts are present
                concepts_found = sum(1 for concept in pattern_data if concept.lower() in chunk_lower)
                if concepts_found > 0:
                    score_boost = (concepts_found / len(pattern_data)) * pattern_weight * 8
                    total_score += score_boost
                    matched_terms.extend([c for c in pattern_data if c.lower() in chunk_lower])
            
            elif pattern_type == 'synonym_expansion':
                # Check for any synonym matches
                synonyms_found = [term for term in pattern_data if term.lower() in chunk_lower]
                if synonyms_found:
                    total_score += pattern_weight * len(synonyms_found)
                    matched_terms.extend(synonyms_found)
            
            elif pattern_type == 'intent_based':
                # Check for intent keywords
                intent_matches = [keyword for keyword in pattern_data if keyword.lower() in chunk_lower]
                if intent_matches:
                    total_score += pattern_weight * 6
                    matched_terms.extend(intent_matches)
            
            elif pattern_type == 'broad_keywords':
                # Check for broad keyword matches
                keyword_matches = [keyword for keyword in pattern_data if keyword.lower() in chunk_lower]
                if keyword_matches:
                    score_boost = min(len(keyword_matches) * pattern_weight, 5)  # Cap the boost
                    total_score += score_boost
                    matched_terms.extend(keyword_matches)
        
        # Only return chunks with a minimum score
        if total_score > 0.5:
            return [ChunkMatch(
                chunk_id=f"chunk_{chunk_idx}",
                text=chunk_text,
                score=total_score,
                matched_terms=list(set(matched_terms)),  # Remove duplicates
                chunk_type='paragraph',
                start_char=chunk_idx * 1000,  # Approximate
                end_char=(chunk_idx + 1) * 1000,
                document_info={'chunk_index': chunk_idx}
            )]
        
        return []

    def enhanced_search(self, query: str, document_text: str) -> List[ChunkMatch]:
        """Perform enhanced search on document text."""
        print(f"Performing enhanced search for: {query}")
        
        # Analyze the query
        analysis = self.analyze_query(query)
        print(f"Query analysis: {analysis['intent']}")
        
        # Search document chunks
        matches = self.search_text(document_text, analysis)
        
        print(f"Found {len(matches)} matches")
        return matches 