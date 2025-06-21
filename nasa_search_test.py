#!/usr/bin/env python3
"""
Test script for enhanced search functionality using NASA Open Source Agreement
"""

import re
from typing import List, Dict, Any

def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF file."""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        # Return sample text for testing
        return """
NASA OPEN SOURCE AGREEMENT VERSION 1.3

This Agreement is a copyright license and not an assignment of copyright. Government retains title to and ownership of the Subject Software.

A. Definitions

"Contributor" means Government or any individual, legal entity, or other entity which has Covered Code directly from Government or from another Contributor and is making a Contribution.

"Contribution" means any software fix, patch, upgrade, modification, enhancement, improvement, translation, abridgment, condensation, or any other form of alteration to Covered Code, and any new software modules or other software components that work in conjunction with Covered Code and are derivative of or link with or to Covered Code, or any portion thereof, and that are intentionally submitted by You to Government for inclusion in Covered Code or are intentionally submitted by You to a Contributor for inclusion in a version of Covered Code maintained by that Contributor.

"Covered Code" means Original Code, Modifications, or the combination of Original Code and Modifications, in each case including portions thereof.

"Government" means, collectively, the United States National Aeronautics and Space Administration and other entities of the United States Government that are making the Subject Software available under this Agreement.

"Licensed Patents" means patent claims licensable by a Contributor which are necessarily infringed by the use or sale of its Contribution alone or when combined with the Subject Software.

"Original Code" means Source Code of computer software code which is described in the Source Code notice required by Exhibit A as Original Code, and which, at the time of its release under this Agreement is not already Covered Code governed by this Agreement.

"Recipient" means anyone who receives the Subject Software under this Agreement, including all Contributors.

"Redistribution" means any of the acts allowed by Section B.1.

"Source Code" means the preferred form of the Covered Code for making modifications to it, including all modules it contains, plus any associated interface definition files, scripts used to control compilation and installation of an executable program or other components, if any, that are used as part of the Covered Code.

"Subject Software" means the Original Code, Modifications, or any respective parts thereof.

"You" (or "Your") refers to an individual or a legal entity exercising rights under, and complying with all of the terms of, this Agreement. For legal entities, "You" includes any entity which controls, is controlled by, or is under common control with You.

B. GRANT OF RIGHTS

Subject to the terms and conditions of this Agreement, including, without limitation, the Non-Commercial Use Limitation and the restrictions set forth in Section B.2, each Contributor hereby grants You a non-exclusive, worldwide, royalty-free license:

1. under intellectual property rights (other than patent or trademark) Licensable by Contributor, to use, reproduce, display, perform, modify and distribute the Subject Software (or portions thereof), with or without Modifications, and/or as part of a Larger Work; and

2. under Patent Claims of such Contributor to make, use, sell, offer for sale, have made, import and otherwise transfer the Subject Software (or portions thereof), where such license applies only to the Patent Claims infringed by the Subject Software (or portions thereof) alone or by combination of the Subject Software with other software or hardware.

C. REQUIREMENTS

A Contributor may choose to offer, and charge a fee for, warranty, support, indemnity and/or liability obligations to one or more Recipients of Covered Code. However, a Contributor may do so only on its own behalf and not on behalf of Government or any other Contributor. A Contributor must make it absolutely clear that any such warranty, support, indemnity and/or liability obligation is offered by that Contributor alone, and further agrees to indemnify Government and every other Contributor for any liability incurred by Government or such other Contributor as a result of warranty, support, indemnity and/or liability terms a Contributor offers.

D. DISTRIBUTION OBLIGATIONS

1. A Contributor may distribute Covered Code, provided that such Contributor:

a) distributes Covered Code under the terms of this Agreement and includes the text of this Agreement with each copy of Covered Code that You distribute, and You must inform recipients of Covered Code that they may obtain a copy of this Agreement from Government. If it is not possible to put such notice in a particular Source Code file due to its structure, then You must include such notice in a location where a user would be likely to look for such a notice;

b) distributes Covered Code in a manner which reasonably allows subsequent Recipients to identify the originator of the Covered Code; and

c) includes a prominent notice stating that the Subject Software is available from Government upon request.

2. A Contributor may distribute Modifications under the terms of this Agreement provided that such Contributor:

a) distributes Modifications under the terms of this Agreement and includes the text of this Agreement with each copy of Modifications that You distribute, and You must inform recipients of Modifications that they may obtain a copy of this Agreement from Government. If it is not possible to put such notice in a particular Source Code file due to its structure, then You must include such notice in a location where a user would be likely to look for such a notice;

b) distributes Modifications in a manner which reasonably allows subsequent Recipients to identify the originator of the Modifications.

E. INABILITY TO COMPLY DUE TO STATUTE OR REGULATION

If it is impossible for Contributor to comply with any of the terms of this Agreement with respect to some or all of the Subject Software due to statute, judicial order, or regulation then Contributor must: (a) comply with the terms of this Agreement to the maximum extent possible; and (b) describe the limitations and the code they affect. Such description must be included in the LEGAL file described in Section F.3 of this Agreement and must be included with all distributions of the Subject Software. Except to the extent prohibited by statute or regulation, such description must be sufficiently detailed for a recipient of ordinary skill to be able to understand it.

F. TERMINATION

1. This Agreement and the rights granted hereunder will terminate automatically if a Recipient fails to comply with terms herein and fails to cure such noncompliance within thirty (30) days of becoming aware of such noncompliance. Upon termination, Recipient agrees to immediately stop any further use, reproduction, modification, or distribution of the Subject Software. All sublicenses to the Subject Software which are properly granted shall survive any termination of this Agreement.

2. In the event of termination under Section F.1 above, all end user license agreements (excluding distributors and resellers) which have been validly granted by You or any distributor hereunder prior to termination shall survive termination.

G. GOVERNMENT USE

The Subject Software was developed under a United States Government contract. Consistent with FAR 12.212 and 41 CFR 227.7202-1 through 227.7202-4, the Subject Software is licensed to the U.S. Government under the same terms of this Agreement.

H. MISCELLANEOUS

1. This Agreement is governed by the laws of the United States and the State in which the Subject Software was developed, excluding the application of the conflict of laws rules of any jurisdiction.

2. This Agreement shall not be governed by the United Nations Convention on Contracts for the International Sale of Goods.

3. This Agreement constitutes the entire agreement between the parties with respect to the Subject Software. However, You may choose to redistribute Source Code and Executable Files under Your own license agreement, consistent with the requirements of this Agreement, in which case the provisions of Your license agreement will apply in addition to those of this Agreement.

4. If any provision of this Agreement shall be deemed unenforceable, invalid, or illegal by a court or agency of competent jurisdiction, then enforcement of this Agreement shall continue with respect to the other provisions.
"""

class EnhancedSearchEngine:
    """Enhanced search engine for legal documents."""
    
    def __init__(self):
        self.legal_synonyms = {
            'accept': ['acknowledge', 'agree', 'consent', 'approve'],
            'acceptance': ['agreement', 'acknowledgment', 'consent'],
            'trigger': ['cause', 'initiate', 'activate', 'start'],
            'responsibility': ['obligation', 'duty', 'liability'],
            'obligations': ['duties', 'responsibilities', 'requirements'],
            'contributor': ['provider', 'supplier', 'author'],
            'recipient': ['user', 'receiver', 'party'],
            'rights': ['permissions', 'privileges', 'entitlements'],
            'license': ['permit', 'authorization', 'permission'],
            'licensed': ['permitted', 'authorized', 'allowed'],
            'distribute': ['provide', 'share', 'disseminate'],
            'distribution': ['sharing', 'dissemination', 'provision'],
            'modifications': ['changes', 'alterations', 'updates'],
            'sublicense': ['relicense', 'secondary license'],
            'requirements': ['conditions', 'obligations', 'mandates'],
            'warranty': ['guarantee', 'assurance'],
            'indemnity': ['protection', 'compensation'],
            'compliance': ['adherence', 'conformity'],
            'noncompliance': ['violation', 'breach'],
            'termination': ['ending', 'cancellation'],
            'governing': ['controlling', 'applicable'],
            'export': ['international', 'foreign'],
            'commercial': ['business', 'trade'],
            'software': ['code', 'program', 'application'],
            'patent': ['intellectual property', 'invention'],
            'copyright': ['intellectual property', 'ownership'],
        }
        
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'this', 'that', 'these', 'those'
        }
    
    def preprocess_query(self, query: str) -> Dict[str, Any]:
        """Preprocess and analyze the query."""
        query_lower = query.lower()
        
        # Extract question type
        question_type = 'general'
        if any(word in query_lower for word in ['what are', 'what is', 'define']):
            question_type = 'definition'
        elif any(word in query_lower for word in ['when', 'under what']):
            question_type = 'conditions'
        elif any(word in query_lower for word in ['can', 'may']):
            question_type = 'permission'
        elif 'what happens' in query_lower:
            question_type = 'consequence'
        
        # Extract key terms
        words = re.findall(r'\b\w+\b', query_lower)
        key_terms = [word for word in words if word not in self.stop_words and len(word) > 2]
        
        # Extract important phrases
        phrases = []
        important_phrases = [
            'subject software', 'source code', 'patent rights', 
            'copyright notice', 'government agency', 'commercial advantage',
            'export license', 'governing law', 'user registration'
        ]
        
        for phrase in important_phrases:
            if phrase in query_lower:
                phrases.append(phrase)
        
        return {
            'original_query': query,
            'question_type': question_type,
            'key_terms': key_terms,
            'phrases': phrases
        }
    
    def search_document(self, document_text: str, query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search document using enhanced techniques."""
        
        # Split document into chunks
        chunks = self._split_into_chunks(document_text)
        
        # Score each chunk
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            score = self._calculate_score(chunk, query_analysis)
            if score > 0:
                scored_chunks.append({
                    'chunk_id': i,
                    'text': chunk,
                    'score': score
                })
        
        # Sort by score and return top results
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        return scored_chunks[:5]
    
    def _split_into_chunks(self, text: str, chunk_size: int = 800) -> List[str]:
        """Split text into manageable chunks."""
        # Split by double newlines (paragraphs) first
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
    
    def _calculate_score(self, chunk: str, query_analysis: Dict[str, Any]) -> float:
        """Calculate relevance score for a chunk."""
        chunk_lower = chunk.lower()
        score = 0
        
        # Score for exact phrases (highest weight)
        for phrase in query_analysis['phrases']:
            if phrase in chunk_lower:
                score += 20
        
        # Score for key terms
        for term in query_analysis['key_terms']:
            if term in chunk_lower:
                score += 5
            
            # Score for synonyms
            if term in self.legal_synonyms:
                for synonym in self.legal_synonyms[term]:
                    if synonym in chunk_lower:
                        score += 3
        
        # Bonus for question type matching
        question_type = query_analysis['question_type']
        if question_type == 'definition' and ('means' in chunk_lower or 'definition' in chunk_lower):
            score += 10
        elif question_type == 'conditions' and ('if' in chunk_lower or 'when' in chunk_lower):
            score += 8
        elif question_type == 'permission' and ('may' in chunk_lower or 'can' in chunk_lower):
            score += 8
        elif question_type == 'consequence' and ('result' in chunk_lower or 'shall' in chunk_lower):
            score += 8
        
        return score

def test_nasa_search():
    """Test the enhanced search with NASA document queries."""
    
    # Load document
    print("Loading NASA Open Source Agreement...")
    document_text = extract_pdf_text('uploads/NASA_Open_Source_Agreement_1.3.pdf')
    print(f"Document loaded: {len(document_text)} characters")
    
    # Initialize search engine
    search_engine = EnhancedSearchEngine()
    
    # Test queries
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
    print("ENHANCED SEARCH RESULTS")
    print("="*80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- QUERY {i} ---")
        print(f"Q: {query}")
        
        # Analyze query
        analysis = search_engine.preprocess_query(query)
        print(f"Type: {analysis['question_type']}")
        print(f"Key terms: {', '.join(analysis['key_terms'][:8])}")
        if analysis['phrases']:
            print(f"Key phrases: {', '.join(analysis['phrases'])}")
        
        # Search document
        results = search_engine.search_document(document_text, analysis)
        
        if results:
            print(f"\nFound {len(results)} relevant sections:")
            
            # Show top 2 results
            for j, result in enumerate(results[:2], 1):
                print(f"\n[Result {j}] Score: {result['score']:.1f}")
                text_preview = result['text'][:300] + "..." if len(result['text']) > 300 else result['text']
                print(f"Text: {text_preview}")
        else:
            print("\nNo relevant sections found.")
        
        print("-" * 60)

if __name__ == "__main__":
    test_nasa_search() 