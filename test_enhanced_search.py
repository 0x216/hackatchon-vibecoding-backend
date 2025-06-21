"""
Test script for the enhanced search system using the NASA Open Source Agreement
"""

import sys
import os
import re
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import Counter

# Add path for imports
sys.path.append('.')

@dataclass
class SearchTerm:
    """Represents a search term with metadata."""
    term: str
    weight: float
    category: str
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
            'trigger': ['cause', 'initiate', 'activate', 'start', 'prompt'],
            'perform': ['execute', 'carry out', 'conduct', 'do', 'implement'],
            'activities': ['actions', 'operations', 'tasks', 'work', 'processes'],
            'define': ['specify', 'describe', 'explain', 'clarify', 'identify'],
            'provide': ['supply', 'give', 'offer', 'furnish', 'deliver'],
            'remove': ['delete', 'eliminate', 'take away', 'extract'],
            'fail': ['not succeed', 'be unable', 'neglect', 'omit'],
            'software': ['code', 'program', 'application', 'system'],
            'source code': ['source', 'code', 'programming code'],
            'copyright': ['intellectual property', 'authorship', 'ownership'],
            'notice': ['notification', 'announcement', 'statement', 'message'],
            'patent': ['intellectual property', 'invention', 'IP'],
            'conditions': ['circumstances', 'situations', 'requirements', 'terms'],
            'happens': ['occurs', 'takes place', 'arises', 'comes about'],
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
        
        # Extract key concepts and terms
        key_terms = self._extract_key_terms(query_lower)
        
        # Generate search variations
        search_terms = self._generate_search_terms(key_terms)
        
        # Identify important phrases
        phrases = self._extract_phrases(query_lower)
        
        # Detect intent
        intent = self._detect_intent(query_lower)
        
        return {
            'original_query': query,
            'intent': intent,
            'key_terms': key_terms,
            'search_terms': search_terms,
            'phrases': phrases,
        }
    
    def _detect_intent(self, query: str) -> str:
        """Detect the intent of the query."""
        if any(word in query for word in ['what are', 'what is', 'define']):
            return 'definition'
        elif any(word in query for word in ['when', 'under what', 'if']):
            return 'conditions'
        elif any(word in query for word in ['can', 'may', 'able to']):
            return 'permission'
        elif any(word in query for word in ['requirements', 'must', 'shall']):
            return 'obligation'
        elif 'what happens' in query:
            return 'consequence'
        else:
            return 'general'
    
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
        
        # Add important bigrams
        phrases = []
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i + 1]}"
            if any(important in bigram for important in 
                  ['source code', 'subject software', 'government agency', 
                   'patent rights', 'copyright notice', 'open source']):
                phrases.append(bigram)
        
        return meaningful_words + phrases
    
    def _generate_search_terms(self, key_terms: List[str]) -> List[SearchTerm]:
        """Generate weighted search terms with synonyms."""
        search_terms = []
        
        for term in key_terms:
            term_lower = term.lower()
            
            # Determine weight based on term importance
            weight = 1.0
            if term_lower in ['contributor', 'recipient', 'software', 'modification', 'license']:
                weight = 2.0
            elif len(term) > 8:  # Longer terms are often more specific
                weight = 1.5
            
            # Get synonyms
            synonyms = self.concept_synonyms.get(term_lower, [])
            
            search_terms.append(SearchTerm(
                term=term,
                weight=weight,
                category='general',
                synonyms=synonyms
            ))
        
        return search_terms
    
    def _extract_phrases(self, query: str) -> List[str]:
        """Extract important phrases from the query."""
        phrases = []
        
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
    
    def search_text(self, text: str, analysis: Dict[str, Any]) -> List[ChunkMatch]:
        """Search text using the analyzed query."""
        chunks = self._split_text_into_chunks(text)
        
        matches = []
        for chunk_idx, chunk_text in enumerate(chunks):
            score = self._score_chunk(chunk_text, analysis)
            if score > 0.5:
                matches.append(ChunkMatch(
                    chunk_id=f"chunk_{chunk_idx}",
                    text=chunk_text,
                    score=score,
                    matched_terms=[],
                    chunk_type='paragraph',
                    start_char=chunk_idx * 1000,
                    end_char=(chunk_idx + 1) * 1000,
                    document_info={'chunk_index': chunk_idx}
                ))
        
        # Sort by score and return top matches
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:5]  # Return top 5 matches
    
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
    
    def _score_chunk(self, chunk_text: str, analysis: Dict[str, Any]) -> float:
        """Score a chunk based on the query analysis."""
        chunk_lower = chunk_text.lower()
        total_score = 0
        
        # Score based on exact phrases
        for phrase in analysis['phrases']:
            if phrase.lower() in chunk_lower:
                total_score += 10  # High score for exact phrases
        
        # Score based on search terms and synonyms
        for term in analysis['search_terms']:
            # Check main term
            if term.term.lower() in chunk_lower:
                total_score += term.weight * 5
            
            # Check synonyms
            for synonym in term.synonyms:
                if synonym.lower() in chunk_lower:
                    total_score += term.weight * 3
        
        # Score based on key terms
        for term in analysis['key_terms']:
            if term.lower() in chunk_lower:
                total_score += 2
        
        return total_score

def load_nasa_document() -> str:
    """Load the NASA document text."""
    try:
        from app.core.ingest.extractors import DocumentExtractorFactory
        extractor = DocumentExtractorFactory()
        result = extractor.extract_text('uploads/NASA_Open_Source_Agreement_1.3.pdf')
        return result.get('text', '')
    except Exception as e:
        print(f"Error loading document: {e}")
        # Return sample text for testing
        return """
        NASA OPEN SOURCE AGREEMENT VERSION 1.3

        A. Definitions
        "Contributor" means Government or any individual, legal entity, or other entity which has Covered Code directly from Government or from another Contributor and is making a Contribution.

        "Contribution" means any software fix, patch, upgrade, modification, enhancement, improvement, translation, abridgment, condensation, or any other form of alteration to Covered Code, and any new software modules or other software components that work in conjunction with Covered Code and are derivative of or link with or to Covered Code, or any portion thereof, and that are intentionally submitted by You to Government for inclusion in Covered Code or are intentionally submitted by You to a Contributor for inclusion in a version of Covered Code maintained by that Contributor.

        "Covered Code" means Original Code, Modifications, or the combination of Original Code and Modifications, in each case including portions thereof.

        "Recipient" means anyone who receives the Subject Software under this Agreement, including all Contributors.

        "Subject Software" means software which is distributed hereunder.

        B. GRANT OF RIGHTS

        1. Subject to the terms and conditions of this Agreement, each Contributor hereby grants to each Recipient a non-exclusive, worldwide, royalty-free copyright license to reproduce, prepare derivative works of, publicly display, publicly perform, distribute and sublicense the Subject Software or portions thereof in any medium with or without modifications, and in Source Code or as compiled bytecode.

        2. Subject to the terms and conditions of this Agreement, each Contributor hereby grants to each Recipient a non-exclusive, worldwide, royalty-free patent license under Licensed Patents to make, use, distribute, sell, offer for sale, import and otherwise transfer the Subject Software or portions thereof. The foregoing license shall not apply to any other patents or patent applications owned or controlled by Contributor.

        C. REQUIREMENTS

        A Contributor may choose to offer, and charge a fee for, warranty, support, indemnity and/or liability obligations to one or more Recipients of Covered Code. However, a Contributor may do so only on its own behalf and not on behalf of Government or any other Contributor. A Contributor must make it absolutely clear that any such warranty, support, indemnity and/or liability obligation is offered by that Contributor alone, and further agrees to indemnify Government and every other Contributor for any liability incurred by Government or such other Contributor as a result of warranty, support, indemnity and/or liability terms a Contributor offers.

        D. DISTRIBUTION OBLIGATIONS

        1. A Contributor may distribute Covered Code, provided that such Contributor:

        a) distributes Covered Code under the terms of this Agreement and includes the text of this Agreement with each copy of Covered Code;

        b) can demonstrate that the Subject Software and any Modifications or other software developed in connection with the Subject Software have been tested in a computer system that adequately and reasonably replicates the operating environment in which the Covered Code will be used by Recipients; and

        c) includes a prominent notice stating that the Subject Software is available from Government upon request.

        E. INABILITY TO COMPLY DUE TO STATUTE OR REGULATION

        If it is impossible for Contributor to comply with any of the terms of this Agreement with respect to some or all of the Subject Software due to statute, judicial order, or regulation then Contributor must: (a) comply with the terms of this Agreement to the maximum extent possible; and (b) describe the limitations and the code they affect. Such description must be included in the LEGAL file described in Section F.3 of this Agreement and must be included with all distributions of the Subject Software. Except to the extent prohibited by statute or regulation, such description must be sufficiently detailed for a recipient of ordinary skill to be able to understand it.

        F. TERMINATION

        1. This Agreement and the rights granted hereunder will terminate automatically if a Recipient fails to comply with terms herein and fails to cure such noncompliance within thirty (30) days of becoming aware of such noncompliance.

        G. GENERAL

        This Agreement shall be governed by and construed in accordance with United States federal law and, to the extent such federal law does not apply, by the law of the jurisdiction in which the Subject Software was developed.
        """

def test_queries():
    """Test the enhanced search with complex queries."""
    
    # Load the document
    print("Loading NASA document...")
    document_text = load_nasa_document()
    print(f"Document loaded: {len(document_text)} characters")
    
    # Initialize the enhanced retriever
    retriever = EnhancedDocumentRetriever()
    
    # Test queries from the user
    test_queries = [
        "What are the key actions that trigger acceptance of the responsibilities and obligations outlined in this Agreement?",
        "Define 'Contributor' and 'Subject Software' as per this agreement.",
        "Under non-patent rights, what activities are Recipients explicitly licensed to perform with the Subject Software?",
        "Regarding patent rights, what activities are Recipients licensed to perform, and how do these rights apply to Modifications combined with Subject Software?",
        "Can a Recipient sublicense the rights granted under this Agreement? If so, under what conditions?",
        "When distributing or redistributing the Subject Software, what are the requirements for including the Agreement and providing source code?",
        "What are the requirements for a Contributor when making an alteration to the Subject Software?",
        "Can a Recipient remove a copyright notice added by a Contributor?",
        "What limitations are placed on Recipients regarding representations about Government Agency endorsement or commercial advantage?",
        "What is the stated purpose of requesting user registration and information about Modifications?",
        "What representations does a Contributor make about their Modifications?",
        "Can a Recipient offer warranty, support, or indemnity for the Subject Software? If so, what are the conditions and their liability?",
        "What happens if a Recipient fails to comply with the terms of this Agreement and does not cure the noncompliance?",
        "What is the governing law for this Agreement?",
        "Does this Agreement provide any export license from the U.S. Government?"
    ]
    
    print("\n" + "="*80)
    print("TESTING ENHANCED SEARCH SYSTEM")
    print("="*80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- Query {i} ---")
        print(f"Q: {query}")
        
        # Analyze the query
        analysis = retriever.analyze_query(query)
        print(f"Intent: {analysis['intent']}")
        print(f"Key terms: {analysis['key_terms'][:5]}")  # Show first 5 terms
        
        # Search for matches
        matches = retriever.search_text(document_text, analysis)
        
        if matches:
            print(f"Found {len(matches)} relevant chunks (showing top 2):")
            for j, match in enumerate(matches[:2], 1):
                print(f"\nMatch {j} (Score: {match.score:.2f}):")
                # Show first 200 characters of the match
                preview = match.text[:200] + "..." if len(match.text) > 200 else match.text
                print(f"Text: {preview}")
        else:
            print("No relevant chunks found.")
        
        print("-" * 50)

if __name__ == "__main__":
    test_queries() 