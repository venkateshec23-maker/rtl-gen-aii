"""
RAG (Retrieval-Augmented Generation) System

Implements semantic search and retrieval of relevant examples
to improve code generation quality.

Usage:
    from python.rag_system import RAGSystem
    
    rag = RAGSystem()
    examples = rag.retrieve_relevant_examples(query)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import Counter
import re


class RAGSystem:
    """Retrieval-Augmented Generation system."""
    
    def __init__(self, base_dir: str = 'training_data'):
        """Initialize RAG system."""
        self.base_dir = Path(base_dir)
        self.designs_dir = self.base_dir / 'designs'
        self.index_dir = self.base_dir / 'rag_index'
        self.index_dir.mkdir(exist_ok=True)
        
        # Load or create index
        self.index = self._load_or_create_index()
    
    def _load_or_create_index(self) -> Dict:
        """Load existing index or create new one."""
        index_file = self.index_dir / 'design_vectors.json'
        
        if index_file.exists():
            with open(index_file) as f:
                return json.load(f)
        
        # Create new index
        return self.create_index()
    
    def extract_features(self, design_data: Dict) -> Dict:
        """
        Extract features from design for vectorization.
        
        Args:
            design_data: Design data
            
        Returns:
            dict: Feature dictionary
        """
        features = {
            'category': design_data['metadata']['category'],
            'complexity': design_data['metadata']['complexity'],
            'bit_width': design_data['metadata']['bit_width'],
            'keywords': set(),
            'operations': set(),
        }
        
        # Extract keywords from description
        desc = design_data['description']['natural_language'].lower()
        features['keywords'].update(re.findall(r'\b\w+\b', desc))
        
        # Extract from tags
        if design_data['metadata'].get('tags'):
            features['keywords'].update(design_data['metadata']['tags'])
        
        # Extract from enhanced metadata
        if 'enhanced_metadata' in design_data:
            if 'keywords' in design_data['enhanced_metadata']:
                features['keywords'].update(design_data['enhanced_metadata']['keywords'])
        
        # Extract operations from code
        code = design_data['code']['rtl'].lower()
        
        operations = ['add', 'subtract', 'multiply', 'shift', 'and', 'or', 'xor', 'compare']
        for op in operations:
            if op in code or op in desc:
                features['operations'].add(op)
        
        # Convert sets to lists for JSON serialization
        features['keywords'] = list(features['keywords'])
        features['operations'] = list(features['operations'])
        
        return features
    
    def create_vocabulary(self, all_features: List[Dict]) -> Dict:
        """
        Create vocabulary from all features.
        
        Args:
            all_features: List of feature dicts
            
        Returns:
            dict: Vocabulary mapping
        """
        vocab = {
            'keywords': set(),
            'operations': set(),
            'categories': set(),
            'complexities': set(),
        }
        
        for features in all_features:
            vocab['keywords'].update(features['keywords'])
            vocab['operations'].update(features['operations'])
            vocab['categories'].add(features['category'])
            vocab['complexities'].add(features['complexity'])
        
        # Convert to lists and create indices
        vocabulary = {
            'keywords': {w: i for i, w in enumerate(sorted(vocab['keywords']))},
            'operations': {w: i for i, w in enumerate(sorted(vocab['operations']))},
            'categories': {w: i for i, w in enumerate(sorted(vocab['categories']))},
            'complexities': {w: i for i, w in enumerate(sorted(vocab['complexities']))},
        }
        
        return vocabulary
    
    def vectorize_features(self, features: Dict, vocabulary: Dict) -> List[float]:
        """
        Convert features to vector.
        
        Args:
            features: Feature dictionary
            vocabulary: Vocabulary mapping
            
        Returns:
            list: Feature vector
        """
        vector = []
        
        # Keywords (binary presence)
        keyword_vec = [0.0] * len(vocabulary['keywords'])
        for keyword in features['keywords']:
            if keyword in vocabulary['keywords']:
                idx = vocabulary['keywords'][keyword]
                keyword_vec[idx] = 1.0
        vector.extend(keyword_vec)
        
        # Operations (binary presence)
        operation_vec = [0.0] * len(vocabulary['operations'])
        for operation in features['operations']:
            if operation in vocabulary['operations']:
                idx = vocabulary['operations'][operation]
                operation_vec[idx] = 1.0
        vector.extend(operation_vec)
        
        # Category (one-hot)
        category_vec = [0.0] * len(vocabulary['categories'])
        if features['category'] in vocabulary['categories']:
            idx = vocabulary['categories'][features['category']]
            category_vec[idx] = 1.0
        vector.extend(category_vec)
        
        # Complexity (one-hot)
        complexity_vec = [0.0] * len(vocabulary['complexities'])
        if features['complexity'] in vocabulary['complexities']:
            idx = vocabulary['complexities'][features['complexity']]
            complexity_vec[idx] = 1.0
        vector.extend(complexity_vec)
        
        # Bit width (normalized)
        bit_width_norm = features['bit_width'] / 64.0  # Normalize to 0-1
        vector.append(bit_width_norm)
        
        return vector
    
    def create_index(self) -> Dict:
        """
        Create search index from all designs.
        
        Returns:
            dict: Search index
        """
        print("Creating RAG index...")
        
        all_designs = []
        all_features = []
        
        # Collect all designs
        categories = ['combinational', 'sequential', 'fsm', 'memory', 'arithmetic', 'control']
        
        for category in categories:
            category_dir = self.designs_dir / category
            if not category_dir.exists():
                continue
            
            for design_file in category_dir.glob('*.json'):
                with open(design_file) as f:
                    design_data = json.load(f)
                
                # Only index verified designs
                if not design_data['metadata'].get('verified', False):
                    continue
                
                features = self.extract_features(design_data)
                
                all_designs.append({
                    'id': design_data['metadata']['id'],
                    'file_path': str(design_file.relative_to(self.base_dir)),
                    'name': design_data['metadata']['name'],
                    'description': design_data['description']['natural_language'],
                })
                
                all_features.append(features)
        
        print(f"  Collected {len(all_designs)} designs")
        
        # Create vocabulary
        vocabulary = self.create_vocabulary(all_features)
        print(f"  Vocabulary size: {sum(len(v) for v in vocabulary.values())} terms")
        
        # Vectorize all designs
        vectors = []
        for features in all_features:
            vector = self.vectorize_features(features, vocabulary)
            vectors.append(vector)
        
        # Create index
        index = {
            'designs': all_designs,
            'vectors': vectors,
            'vocabulary': vocabulary,
            'vector_dim': len(vectors[0]) if vectors else 0,
        }
        
        # Save index
        index_file = self.index_dir / 'design_vectors.json'
        with open(index_file, 'w') as f:
            json.dump(index, f)
        
        print(f"  ✓ Index saved: {index_file}")
        
        return index
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            float: Similarity score (0-1)
        """
        # Convert to numpy arrays
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def retrieve_relevant_examples(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """
        Retrieve relevant design examples.
        
        Args:
            query: Query description
            top_k: Number of results
            min_similarity: Minimum similarity threshold
            
        Returns:
            list: Relevant designs with similarity scores
        """
        if not self.index or not self.index['designs']:
            return []
        
        # Extract features from query
        query_features = {
            'category': 'unknown',
            'complexity': 'medium',
            'bit_width': 8,
            'keywords': re.findall(r'\b\w+\b', query.lower()),
            'operations': [],
        }
        
        # Vectorize query
        query_vector = self.vectorize_features(query_features, self.index['vocabulary'])
        
        # Calculate similarities
        similarities = []
        for i, design_vector in enumerate(self.index['vectors']):
            similarity = self.cosine_similarity(query_vector, design_vector)
            
            if similarity >= min_similarity:
                design_info = self.index['designs'][i].copy()
                design_info['similarity'] = similarity
                similarities.append(design_info)
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_k]
    
    def get_index_statistics(self) -> Dict:
        """Get index statistics."""
        if not self.index:
            return {'indexed_designs': 0}
        
        return {
            'indexed_designs': len(self.index.get('designs', [])),
            'vector_dimension': self.index.get('vector_dim', 0),
            'vocabulary_size': sum(len(v) for v in self.index.get('vocabulary', {}).values()),
        }


# ============================================================================
# SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("RAG System Self-Test\n")
    
    # Check if numpy is available
    try:
        import numpy as np
    except ImportError:
        print("⚠ numpy not installed. Install with: pip install numpy")
        print("Continuing with limited functionality...\n")
    
    rag = RAGSystem()
    
    # Test 1: Create or load index
    print("Test 1: Index statistics")
    print("=" * 70)
    stats = rag.get_index_statistics()
    print(f"Indexed designs: {stats['indexed_designs']}")
    print(f"Vector dimension: {stats['vector_dimension']}")
    print(f"Vocabulary size: {stats['vocabulary_size']}")
    
    # Test 2: Retrieve relevant examples
    print("\nTest 2: Retrieve relevant examples")
    print("=" * 70)
    
    queries = [
        "8-bit adder with carry",
        "counter with reset",
        "state machine for traffic light",
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        results = rag.retrieve_relevant_examples(query, top_k=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['name']} (similarity: {result['similarity']:.3f})")
        else:
            print("  No results found")
    
    print("\n✓ Self-test complete")
