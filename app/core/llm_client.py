"""
Enhanced Google Gemini API client optimized for insurance document processing
with sophisticated prompt engineering and advanced context management.
"""

import asyncio
import logging
import time
import re
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.exceptions import LLMProcessingError
from config.settings import get_settings

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Query type classification for optimized prompt selection."""
    GRACE_PERIOD = "grace_period"
    WAITING_PERIOD = "waiting_period"
    COVERAGE_DETAILS = "coverage_details"
    EXCLUSIONS = "exclusions"
    NUMERICAL_LIMITS = "numerical_limits"
    DEFINITIONS = "definitions"
    UIN_REGULATORY = "uin_regulatory"
    AIR_AMBULANCE = "air_ambulance"
    MATERNITY_WELLBABY = "maternity_wellbaby"
    TABLE_BENEFITS = "table_benefits"
    GENERAL = "general"

@dataclass
class LLMResponse:
    """Enhanced response from LLM processing with comprehensive metadata."""
    text: str
    tokens_used: int
    processing_time_ms: float
    model_used: str
    query_type: QueryType = QueryType.GENERAL
    confidence_score: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

class LLMClient:
    """
    Advanced Google Gemini API client optimized for insurance document analysis
    with sophisticated prompt engineering and context management.
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp", rate_limit: int = 15):
        self.api_key = api_key
        self.model_name = model_name  # Using the latest experimental model
        self.rate_limit = rate_limit
        self.settings = get_settings()
        
        # Enhanced rate limiting and usage tracking
        self.request_times: List[float] = []
        self.daily_tokens_used = 0
        self.last_reset_date = time.strftime("%Y-%m-%d")
        self.request_count = 0
        self.error_count = 0
        
        # Initialize Gemini with enhanced configuration
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # Optimized safety settings for insurance documents
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"  # More permissive for business documents
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH", 
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"  # More permissive for technical content
            }
        ]
        
        # Enhanced generation configuration
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,        # Low temperature for factual accuracy
            max_output_tokens=2048, # Increased for detailed responses
            top_p=0.8,             # Balanced creativity vs accuracy
            top_k=10,              # Limited vocabulary for consistency
            candidate_count=1       # Single response for efficiency
        )
        
        # Query type classification patterns
        self.query_patterns = {
            QueryType.GRACE_PERIOD: [
                r'grace\s*period', r'payment\s*grace', r'premium\s*grace', r'renewal\s*grace',
                r'thirty\s*days?\s*grace', r'30\s*days?\s*grace', r'payment\s*window'
            ],
            QueryType.WAITING_PERIOD: [
                r'waiting\s*period', r'wait\s*period', r'exclusion\s*period', r'cooling\s*period',
                r'\d+\s*months?\s*waiting', r'\d+\s*years?\s*waiting', r'continuous\s*coverage'
            ],
            QueryType.COVERAGE_DETAILS: [
                r'coverage', r'covered', r'benefits?', r'indemnity', r'compensation',
                r'reimbursement', r'what\s*is\s*covered', r'coverage\s*scope'
            ],
            QueryType.EXCLUSIONS: [
                r'exclusion', r'excluded', r'not\s*covered', r'exception', r'limitation',
                r'list.*exclusion', r'what.*not.*covered', r'circumstances.*not.*covered'
            ],
            QueryType.NUMERICAL_LIMITS: [
                r'limit', r'maximum', r'minimum', r'percentage', r'\d+%', r'sub[\-\s]?limit',
                r'room\s*rent.*limit', r'icu.*limit', r'1%', r'2%', r'5%', r'co[\-\s]?payment'
            ],
            QueryType.DEFINITIONS: [
                r'define', r'definition', r'what\s*is', r'how.*define', r'meaning\s*of',
                r'hospital.*define', r'what.*mean'
            ],
            QueryType.UIN_REGULATORY: [
                r'uin', r'unique\s*identification', r'base\s*product', r'regulatory',
                r'authority', r'licensed?', r'certification', r'approval'
            ],
            QueryType.AIR_AMBULANCE: [
                r'air\s*ambulance', r'helicopter', r'aviation', r'medical\s*helicopter',
                r'air\s*medical', r'emergency\s*aviation', r'flight\s*ambulance'
            ],
            QueryType.MATERNITY_WELLBABY: [
                r'maternity', r'pregnancy', r'well\s*mother', r'well\s*baby', r'newborn',
                r'infant', r'childbirth', r'delivery', r'baby\s*care'
            ],
            QueryType.TABLE_BENEFITS: [
                r'table\s*of\s*benefits', r'benefit\s*table', r'schedule', r'benefit\s*schedule',
                r'coverage\s*table', r'payment\s*mode'
            ]
        }
        
        logger.info(f"Enhanced LLM client initialized with model: {model_name}")
    
    def _classify_query_type(self, question: str) -> QueryType:
        """Classify query type for optimized prompt selection."""
        question_lower = question.lower()
        
        # Score each query type based on pattern matches
        type_scores = {}
        for query_type, patterns in self.query_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, question_lower))
                score += matches
            
            if score > 0:
                type_scores[query_type] = score
        
        # Return the highest scoring type or GENERAL if no matches
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        return QueryType.GENERAL
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[str] = None,
        query_type: QueryType = QueryType.GENERAL,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """
        Generate enhanced response using Gemini API with sophisticated configuration.
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Check rate limits
            await self._check_rate_limits()
            
            # Construct optimized prompt
            full_prompt = self._construct_enhanced_prompt(prompt, context, query_type)
            
            # Adjust generation config for query type
            config = self._get_query_specific_config(query_type, max_tokens, temperature)
            
            # Generate response with advanced retry logic
            response = await self._generate_with_enhanced_retry(full_prompt, config)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Extract and process response
            response_text = self._process_response_text(response)
            
            # Enhanced token estimation
            estimated_tokens = self._estimate_tokens(full_prompt, response_text)
            self._update_token_usage(estimated_tokens)
            
            # Record request time for rate limiting
            self.request_times.append(time.time())
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(response_text, query_type)
            
            result = LLMResponse(
                text=response_text,
                tokens_used=estimated_tokens,
                processing_time_ms=processing_time,
                model_used=self.model_name,
                query_type=query_type,
                confidence_score=confidence,
                metadata={
                    'temperature': config.temperature,
                    'prompt_length': len(full_prompt),
                    'response_length': len(response_text),
                    'request_count': self.request_count,
                    'query_type': query_type.value
                }
            )
            
            logger.info(f"Generated {query_type.value} response in {processing_time:.2f}ms, "
                       f"~{estimated_tokens} tokens, confidence: {confidence:.2f}")
            return result
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Enhanced LLM generation failed: {e}")
            raise LLMProcessingError(f"Failed to generate response: {str(e)}")
    
    async def answer_question_with_context(
        self, 
        question: str, 
        context_chunks: List[Dict],
        document_info: Optional[Dict] = None
    ) -> str:
        """
        Answer questions with sophisticated prompt engineering and context management.
        """
        try:
            # Classify query type for optimized processing
            query_type = self._classify_query_type(question)
            
            # Prepare enhanced context
            context_text, sources = self._prepare_enhanced_context(context_chunks, query_type)
            
            # Create specialized prompt based on query type
            prompt = self._create_specialized_qa_prompt(question, context_text, query_type, document_info)
            
            # Generate response with query-specific configuration
            response = await self.generate_response(
                prompt, 
                context=context_text,
                query_type=query_type,
                temperature=0.05 if query_type in [QueryType.NUMERICAL_LIMITS, QueryType.UIN_REGULATORY] else 0.1
            )
            
            # Post-process response based on query type
            final_answer = self._post_process_response(response.text, query_type)
            
            return final_answer.strip()
            
        except Exception as e:
            logger.error(f"Enhanced question answering failed: {e}")
            raise LLMProcessingError(f"Failed to answer question: {str(e)}")
    
    def _construct_enhanced_prompt(
        self, 
        prompt: str, 
        context: Optional[str] = None, 
        query_type: QueryType = QueryType.GENERAL
    ) -> str:
        """Construct sophisticated prompts optimized for different query types."""
        if not context:
            return prompt
        
        # Base structure with query-type specific instructions
        base_prompt = f"""You are a specialized insurance document analyst with expertise in policy interpretation and regulatory compliance.

CONTEXT INFORMATION:
{context}

QUERY TYPE: {query_type.value.upper()}
QUESTION: {prompt}

"""
        
        # Add query-type specific instructions
        instructions = self._get_query_specific_instructions(query_type)
        
        return base_prompt + instructions
    
    def _get_query_specific_instructions(self, query_type: QueryType) -> str:
        """Get specialized instructions for different query types."""
        
        instructions = {
            QueryType.GRACE_PERIOD: """
SPECIALIZED INSTRUCTIONS FOR GRACE PERIOD QUERIES:
1. Look specifically for "grace period", "thirty days", "30 days", "payment grace"
2. Search in sections about premium payment, renewal, and policy continuation
3. Extract EXACT timeframes mentioned (e.g., "thirty days", "30 days")
4. Include any conditions or requirements for grace period applicability
5. If found, state the exact period and any associated conditions
6. Focus on premium payment deadlines and policy continuity rules

ANSWER FORMAT: Start with the specific grace period duration, then explain conditions if any.
""",
            
            QueryType.WAITING_PERIOD: """
SPECIALIZED INSTRUCTIONS FOR WAITING PERIOD QUERIES:
1. Search for "waiting period", "36 months", "24 months", "2 years", "continuous coverage"
2. Look in exclusions sections (often 4.2) and definitions
3. Identify SPECIFIC timeframes for different conditions (PED, maternity, surgery, etc.)
4. Note any exceptions or conditions that modify waiting periods
5. Extract exact periods: "thirty-six (36) months", "24 months", "2 years"
6. Distinguish between different types of waiting periods

ANSWER FORMAT: State the specific waiting period with exact timeframe and what it applies to.
""",
            
            QueryType.NUMERICAL_LIMITS: """
SPECIALIZED INSTRUCTIONS FOR NUMERICAL LIMITS:
1. Search for percentages (1%, 2%, 5%, 10%, 20%, 50%), amounts, and numerical restrictions
2. Look in "Table of Benefits", sub-limits sections, and Plan descriptions
3. Extract EXACT numbers and percentages as written
4. Identify what each limit applies to (room rent, ICU, co-pay, etc.)
5. Note any Plan-specific variations (Plan A, Plan B, etc.)
6. Include currency amounts and calculation methods

ANSWER FORMAT: State the exact percentage or amount, specify what it applies to, and mention any Plan variations.
""",
            
            QueryType.UIN_REGULATORY: """
SPECIALIZED INSTRUCTIONS FOR UIN/REGULATORY QUERIES:
1. Search for alphanumeric codes like "ICIHLIP22012V012223", "EDLHLGP21462V032021"
2. Look for "UIN", "base product", "add-on", "unique identification number"
3. Search regulatory sections, headers, footers, and document metadata
4. Extract COMPLETE alphanumeric codes exactly as written
5. Distinguish between base product UIN and add-on UIN
6. Look for licensing and authority requirements

ANSWER FORMAT: Provide the complete UIN code exactly as it appears in the document.
""",
            
            QueryType.AIR_AMBULANCE: """
SPECIALIZED INSTRUCTIONS FOR AIR AMBULANCE QUERIES:
1. Search for "air ambulance", "150 km", "helicopter", "aviation ambulance"
2. Look for distance limits, licensing requirements, and payment calculations
3. Extract specific distances ("150 km", "one hundred fifty kilometers")
4. Find proportionate payment calculations and examples
5. Identify licensing authority requirements
6. Look for exclusions and limitations specific to air ambulance

ANSWER FORMAT: Provide specific details about distances, payments, or requirements as asked.
""",
            
            QueryType.MATERNITY_WELLBABY: """
SPECIALIZED INSTRUCTIONS FOR MATERNITY/WELL BABY QUERIES:
1. Search for "well mother", "well baby", "maternity", "pregnancy", "newborn"
2. Look for period options, routine care definitions, and coverage scope
3. Extract specific timeframes and coverage periods
4. Identify what routine medical care and preventive care include
5. Find exclusions specific to maternity/baby care
6. Look for multiple birth provisions and sum insured implications

ANSWER FORMAT: Provide specific coverage details, timeframes, and any conditions mentioned.
""",
            
            QueryType.EXCLUSIONS: """
SPECIALIZED INSTRUCTIONS FOR EXCLUSIONS:
1. Search exclusions sections (often 4.1, 4.2, etc.) and "not covered" statements
2. Compile comprehensive lists of excluded items
3. Look for condition-specific exclusions and general exclusions
4. Extract exact wording of exclusions
5. Note any exceptions to exclusions
6. Identify circumstances where coverage is denied

ANSWER FORMAT: Provide a comprehensive list of exclusions as they appear in the document.
""",
            
            QueryType.DEFINITIONS: """
SPECIALIZED INSTRUCTIONS FOR DEFINITIONS:
1. Search definitions sections (often Section 2) and glossaries
2. Look for specific criteria and requirements in definitions
3. Extract complete definitions with all conditions
4. For "Hospital" definitions, include bed requirements, staffing, facilities
5. Note any Plan-specific variations in definitions
6. Include regulatory or qualification requirements

ANSWER FORMAT: Provide the complete definition with all specified criteria and requirements.
""",
            
            QueryType.TABLE_BENEFITS: """
SPECIALIZED INSTRUCTIONS FOR TABLE/BENEFITS QUERIES:
1. Search "Table of Benefits", benefit schedules, and coverage tables
2. Extract information from structured data and benefit summaries
3. Look for payment modes, reimbursement methods, and claim procedures
4. Identify Plan-specific benefit variations
5. Find percentage-based benefits and calculation methods
6. Note any special conditions or approval requirements

ANSWER FORMAT: Provide specific benefit information or payment details as requested.
""",
            
            QueryType.COVERAGE_DETAILS: """
SPECIALIZED INSTRUCTIONS FOR COVERAGE QUERIES:
1. Search benefit sections (often 3.1.x) and coverage descriptions
2. Identify what is covered, conditions for coverage, and scope of benefits
3. Extract specific coverage criteria and eligibility requirements
4. Note any limitations or sub-limits within coverage
5. Look for approval requirements and claim procedures
6. Distinguish between different types of coverage (inpatient, outpatient, etc.)

ANSWER FORMAT: Clearly explain what is covered and under what conditions.
""",
            
            QueryType.GENERAL: """
GENERAL INSTRUCTIONS:
1. Analyze the context thoroughly for relevant information
2. Provide specific, factual answers based on document content
3. Extract exact numbers, timeframes, and conditions when available
4. If information is partial, combine related details for a complete answer
5. Only state "information not available" after thorough search
6. Be precise and concise in your response

ANSWER FORMAT: Provide a clear, factual answer based on the available information.
"""
        }
        
        return instructions.get(query_type, instructions[QueryType.GENERAL])
    
    def _create_specialized_qa_prompt(
        self, 
        question: str, 
        context: str, 
        query_type: QueryType,
        document_info: Optional[Dict] = None
    ) -> str:
        """Create highly specialized prompts for different query types."""
        
        doc_type = document_info.get('file_type', 'insurance document') if document_info else 'insurance document'
        
        # Enhanced base prompt with sophisticated instructions
        base_prompt = f"""You are an expert insurance document analyst specializing in {query_type.value.replace('_', ' ')} queries. Your task is to provide precise, accurate answers based exclusively on the provided document context.

DOCUMENT TYPE: {doc_type}
QUERY CLASSIFICATION: {query_type.value.upper()}

CONTEXT FROM DOCUMENT:
{context}

QUESTION: {question}

ANALYSIS FRAMEWORK:
1. SYSTEMATIC SEARCH: Examine ALL provided context sections methodically
2. EXACT EXTRACTION: When numbers, periods, or codes are found, reproduce them EXACTLY
3. COMPREHENSIVE COVERAGE: Look across definitions, benefits, exclusions, and tables
4. CONTEXTUAL INTEGRATION: Combine related information from multiple sections when needed
5. PRECISION REQUIREMENT: State specific timeframes, amounts, percentages, and conditions
6. SOURCE VERIFICATION: Base answers only on explicitly stated information

"""
        
        # Add query-specific processing instructions
        specialized_instructions = self._get_specialized_processing_instructions(query_type)
        
        # Add response formatting requirements
        format_instructions = self._get_response_format_instructions(query_type)
        
        return base_prompt + specialized_instructions + format_instructions
    
    def _get_specialized_processing_instructions(self, query_type: QueryType) -> str:
        """Get specialized processing instructions for different query types."""
        
        processing_map = {
            QueryType.GRACE_PERIOD: """
GRACE PERIOD PROCESSING:
- Search: "grace period", "thirty days", "payment grace", "premium extension"
- Extract: Exact timeframes and renewal conditions
- Focus: Premium payment deadlines and policy continuity
""",
            
            QueryType.WAITING_PERIOD: """
WAITING PERIOD PROCESSING:
- Search: Exclusions sections, "36 months", "24 months", "continuous coverage"
- Extract: Specific periods for PED, maternity, surgery, etc.
- Focus: Different waiting period types and their applications
""",
            
            QueryType.NUMERICAL_LIMITS: """
NUMERICAL LIMITS PROCESSING:
- Search: Table of Benefits, percentage mentions (1%, 2%, 5%, 10%, 20%, 50%)
- Extract: Exact percentages, amounts, and calculation methods
- Focus: Plan-specific variations and sub-limits
""",
            
            QueryType.UIN_REGULATORY: """
UIN/REGULATORY PROCESSING:
- Search: Document headers, footers, regulatory sections
- Extract: Complete alphanumeric codes (e.g., ICIHLIP22012V012223)  
- Focus: Base product vs add-on identification
""",
            
            QueryType.AIR_AMBULANCE: """
AIR AMBULANCE PROCESSING:
- Search: Distance mentions, "150 km", licensing requirements
- Extract: Specific distances, proportionate calculations, authority requirements
- Focus: Coverage limits and regulatory compliance
""",
            
            QueryType.MATERNITY_WELLBABY: """
MATERNITY/WELL BABY PROCESSING:
- Search: "well mother", "well baby", period options, routine care definitions
- Extract: Coverage periods, care inclusions, exclusions
- Focus: Comprehensive coverage scope and conditions
""",
            
            QueryType.EXCLUSIONS: """
EXCLUSIONS PROCESSING:
- Search: Exclusions sections (4.1, 4.2), "not covered" statements
- Extract: Complete exclusion lists and conditions
- Focus: Comprehensive compilation of all exclusions
""",
            
            QueryType.DEFINITIONS: """
DEFINITIONS PROCESSING:
- Search: Definitions sections (Section 2), criteria specifications
- Extract: Complete definitions with all requirements
- Focus: Detailed criteria and qualification requirements
""",
            
            QueryType.TABLE_BENEFITS: """
TABLE/BENEFITS PROCESSING:
- Search: Structured data, benefit schedules, payment information
- Extract: Specific benefit details and payment procedures
- Focus: Plan variations and special conditions
""",
            
            QueryType.COVERAGE_DETAILS: """
COVERAGE PROCESSING:
- Search: Benefit sections (3.1.x), coverage descriptions
- Extract: Coverage scope, conditions, and limitations
- Focus: Comprehensive coverage explanation
""",
            
            QueryType.GENERAL: """
GENERAL PROCESSING:
- Search: All context sections systematically
- Extract: Relevant information based on question focus
- Focus: Comprehensive and accurate response
"""
        }
        
        return processing_map.get(query_type, processing_map[QueryType.GENERAL])
    
    def _get_response_format_instructions(self, query_type: QueryType) -> str:
        """Get response formatting instructions for different query types."""
        
        format_map = {
            QueryType.GRACE_PERIOD: """
RESPONSE FORMAT:
Provide the specific grace period duration first, followed by any conditions. Example: "A grace period of thirty days is provided for premium payment after the due date..."
""",
            
            QueryType.WAITING_PERIOD: """
RESPONSE FORMAT:
State the specific waiting period with exact timeframe and application. Example: "There is a waiting period of thirty-six (36) months for pre-existing diseases..."
""",
            
            QueryType.NUMERICAL_LIMITS: """
RESPONSE FORMAT:
State the exact percentage or amount with its application. Example: "Room rent is capped at 1% of the Sum Insured for Plan A..."
""",
            
            QueryType.UIN_REGULATORY: """
RESPONSE FORMAT:
Provide the complete UIN code exactly as it appears. Example: "The UIN for this policy is ICIHLIP22012V012223..."
""",
            
            QueryType.AIR_AMBULANCE: """
RESPONSE FORMAT:
Provide specific details about the air ambulance aspect asked. Include exact distances, percentages, or requirements.
""",
            
            QueryType.MATERNITY_WELLBABY: """
RESPONSE FORMAT:
Explain the coverage scope, periods, or conditions clearly. Include specific timeframes and inclusions/exclusions.
""",
            
            QueryType.EXCLUSIONS: """
RESPONSE FORMAT:
List the exclusions clearly and comprehensively as they appear in the document.
""",
            
            QueryType.DEFINITIONS: """
RESPONSE FORMAT:
Provide the complete definition with all specified criteria and requirements.
""",
            
            QueryType.TABLE_BENEFITS: """
RESPONSE FORMAT:
Provide the specific benefit information or payment details as requested from tables or schedules.
""",
            
            QueryType.COVERAGE_DETAILS: """
RESPONSE FORMAT:
Clearly explain what is covered and under what conditions, including any limitations.
""",
            
            QueryType.GENERAL: """
RESPONSE FORMAT:
Provide a clear, factual, and concise answer based on the available information.
"""
        }
        
        common_suffix = """
CRITICAL REQUIREMENTS:
- Answer in ONE clear, comprehensive sentence when possible
- Include specific numbers, timeframes, and conditions exactly as stated
- Only state "information not available" after thorough analysis
- Be precise and avoid unnecessary elaboration

YOUR ANSWER:"""
        
        return format_map.get(query_type, format_map[QueryType.GENERAL]) + common_suffix
    
    def _prepare_enhanced_context(
        self, 
        context_chunks: List[Dict], 
        query_type: QueryType
    ) -> Tuple[str, List[str]]:
        """Prepare enhanced context with query-type specific optimization."""
        if not context_chunks:
            return "", []
        
        # Sort and filter chunks based on relevance and query type
        relevant_chunks = self._filter_chunks_by_query_type(context_chunks, query_type)
        
        # Sort by combined relevance score
        sorted_chunks = sorted(
            relevant_chunks, 
            key=lambda x: (x.get('score', 0) + x.get('type_relevance', 0)), 
            reverse=True
        )
        
        # Prepare context with enhanced formatting
        context_parts = []
        sources_used = []
        
        # Use more chunks for complex query types
        chunk_limit = self._get_chunk_limit(query_type)
        
        for i, chunk in enumerate(sorted_chunks[:chunk_limit], 1):
            text = chunk.get('text', '').strip()
            if text:
                # Enhanced context formatting with metadata
                chunk_info = f"[SECTION {i}]"
                if 'matched_query' in chunk:
                    chunk_info += f" [MATCHED: {chunk['matched_query'][:30]}...]"
                
                context_parts.append(f"{chunk_info}\n{text}")
                sources_used.append(f"Section {i}")
        
        enhanced_context = "\n\n".join(context_parts)
        
        return enhanced_context, sources_used
    
    def _filter_chunks_by_query_type(self, chunks: List[Dict], query_type: QueryType) -> List[Dict]:
        """Filter and score chunks based on query type relevance."""
        # Query-type specific keywords for additional relevance scoring
        type_keywords = {
            QueryType.GRACE_PERIOD: ['grace', 'premium', 'payment', 'thirty', 'renewal'],
            QueryType.WAITING_PERIOD: ['waiting', 'months', 'years', 'continuous', 'exclusion'],
            QueryType.NUMERICAL_LIMITS: ['%', 'limit', 'maximum', 'minimum', 'room', 'icu', 'co-payment', 'copay', 'base'],
            QueryType.UIN_REGULATORY: ['uin', 'product', 'base', 'authority', 'licensed'],
            QueryType.AIR_AMBULANCE: ['air', 'ambulance', 'helicopter', 'distance', 'km'],
            QueryType.MATERNITY_WELLBABY: ['mother', 'baby', 'maternity', 'newborn', 'routine'],
            QueryType.EXCLUSIONS: ['exclusion', 'excluded', 'not covered', 'exception'],
            QueryType.DEFINITIONS: ['definition', 'means', 'hospital', 'qualified', 'inpatient', 'beds'],
            QueryType.TABLE_BENEFITS: ['table', 'benefits', 'schedule', 'payment'],
            QueryType.COVERAGE_DETAILS: ['coverage', 'covered', 'benefits', 'indemnity']
        }
        
        keywords = type_keywords.get(query_type, [])
        
        enhanced_chunks = []
        for chunk in chunks:
            text_lower = chunk.get('text', '').lower()
            
            # Calculate type relevance score
            type_relevance = sum(1 for keyword in keywords if keyword in text_lower)
            type_relevance = min(1.0, type_relevance * 0.1)  # Normalize to 0-1
            
            # Add type relevance to chunk
            enhanced_chunk = chunk.copy()
            enhanced_chunk['type_relevance'] = type_relevance
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def _get_chunk_limit(self, query_type: QueryType) -> int:
        """Get optimal chunk limit based on query type complexity."""
        complex_types = [
            QueryType.EXCLUSIONS, 
            QueryType.TABLE_BENEFITS, 
            QueryType.COVERAGE_DETAILS,
            QueryType.MATERNITY_WELLBABY
        ]
        
        if query_type in complex_types:
            return 8  # More chunks for complex queries
        else:
            return 6  # Standard chunk limit
    
    def _get_query_specific_config(
        self, 
        query_type: QueryType, 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> genai.types.GenerationConfig:
        """Get query-type specific generation configuration."""
        
        # Base configuration
        config = genai.types.GenerationConfig(
            temperature=temperature or 0.1,
            max_output_tokens=max_tokens or 2048,
            top_p=0.8,
            top_k=10,
            candidate_count=1
        )
        
        # Query-type specific adjustments
        if query_type in [QueryType.NUMERICAL_LIMITS, QueryType.UIN_REGULATORY]:
            config.temperature = 0.05  # Very low for factual precision
            config.top_k = 5  # More focused vocabulary
        elif query_type == QueryType.EXCLUSIONS:
            config.max_output_tokens = 3000  # More tokens for comprehensive lists
        elif query_type in [QueryType.DEFINITIONS, QueryType.COVERAGE_DETAILS]:
            config.max_output_tokens = 2500  # More tokens for detailed explanations
        
        return config
    
    @retry(
        stop=stop_after_attempt(4),  # Increased retry attempts
        wait=wait_exponential(multiplier=1, min=2, max=15)
    )
    async def _generate_with_enhanced_retry(
        self, 
        prompt: str, 
        config: genai.types.GenerationConfig
    ):
        """Generate response with enhanced retry logic and error handling - COMPATIBILITY FIXED."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    prompt,
                    safety_settings=self.safety_settings,
                    generation_config=config
                )
            )
            
            # Enhanced response validation
            if not response.candidates:
                raise LLMProcessingError("No response candidates generated")
            
            candidate = response.candidates[0]
            
            # Check finish reason with compatibility handling
            finish_reason = candidate.finish_reason
            
            # Convert finish_reason to string for comparison (handles different library versions)
            finish_reason_str = str(finish_reason).lower()
            
            if 'safety' in finish_reason_str:
                logger.warning("Response blocked by safety filters, retrying with adjusted prompt")
                raise LLMProcessingError("Response blocked by safety filters")
            elif 'max_tokens' in finish_reason_str or 'length' in finish_reason_str:
                logger.warning("Response truncated due to token limit")
            elif 'stop' not in finish_reason_str and 'finish' not in finish_reason_str:
                logger.warning(f"Unexpected finish reason: {finish_reason}")
            
            return response
            
        except Exception as e:
            logger.warning(f"Enhanced LLM generation attempt failed: {e}")
            raise
    
    def _process_response_text(self, response) -> str:
        """Process and clean response text."""
        if hasattr(response, 'text'):
            text = response.text
        elif response.candidates and len(response.candidates) > 0:
            text = response.candidates[0].content.parts[0].text
        else:
            text = str(response)
        
        # Clean and normalize response
        text = text.strip()
        
        # Remove common artifacts
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold formatting
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        return text
    
    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Enhanced token estimation with better accuracy."""
        # More accurate token estimation (roughly 1 token per 3-4 characters)
        total_chars = len(prompt) + len(response)
        estimated_tokens = int(total_chars / 3.5)
        
        # Add overhead for formatting and system prompts
        estimated_tokens = int(estimated_tokens * 1.2)
        
        return estimated_tokens
    
    def _calculate_confidence_score(self, response_text: str, query_type: QueryType) -> float:
        """Calculate confidence score based on response characteristics."""
        base_confidence = 0.5
        
        # Length-based confidence
        if len(response_text) > 50:
            base_confidence += 0.2
        
        # Specificity indicators
        if re.search(r'\d+', response_text):  # Contains numbers
            base_confidence += 0.1
        
        if 'exactly' in response_text.lower() or 'specifically' in response_text.lower():
            base_confidence += 0.1
        
        # Query-type specific confidence adjustments
        if query_type == QueryType.NUMERICAL_LIMITS and re.search(r'\d+%', response_text):
            base_confidence += 0.1
        elif query_type == QueryType.UIN_REGULATORY and re.search(r'[A-Z]{2,}\d{2,}', response_text):
            base_confidence += 0.15
        
        # Uncertainty indicators
        if 'information not available' in response_text.lower():
            base_confidence = 0.1
        elif 'may' in response_text.lower() or 'might' in response_text.lower():
            base_confidence -= 0.1
        
        return min(1.0, max(0.0, base_confidence))
    
    def _post_process_response(self, response_text: str, query_type: QueryType) -> str:
        """Post-process response based on query type."""
        # Remove common LLM prefixes
        prefixes_to_remove = [
            "Based on the context provided, ",
            "According to the document, ",
            "The document states that ",
            "Answer: ",
            "Based on the provided context, ",
            "From the document, ",
            "The policy document indicates that ",
            "Based on the insurance document, ",
            "According to the policy, "
        ]
        
        for prefix in prefixes_to_remove:
            if response_text.lower().startswith(prefix.lower()):
                response_text = response_text[len(prefix):].strip()
        
        # Ensure proper capitalization
        if response_text and response_text[0].islower():
            response_text = response_text[0].upper() + response_text[1:]
        
        # Ensure proper punctuation
        if response_text and response_text[-1] not in '.!?':
            response_text += '.'
        
        # Query-type specific post-processing
        if query_type == QueryType.NUMERICAL_LIMITS:
            # Ensure percentages are clearly formatted
            response_text = re.sub(r'(\d+)\s*percent', r'\1%', response_text)
        elif query_type == QueryType.UIN_REGULATORY:
            # Ensure UIN codes are properly formatted
            response_text = re.sub(r'([A-Z]{2,})(\d{2,}[A-Z0-9]*)', r'\1\2', response_text)
        
        return response_text
    
    async def _check_rate_limits(self):
        """Enhanced rate limiting with better tracking."""
        current_time = time.time()
        
        # Clean old request times (older than 1 minute)
        self.request_times = [
            req_time for req_time in self.request_times
            if current_time - req_time < 60
        ]
        
        # Check requests per minute limit with buffer
        if len(self.request_times) >= self.rate_limit - 1:  # Leave 1 request buffer
            wait_time = 61 - (current_time - self.request_times[0])  # Wait full minute + 1 second
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Check daily token limit
        current_date = time.strftime("%Y-%m-%d")
        if current_date != self.last_reset_date:
            self.daily_tokens_used = 0
            self.last_reset_date = current_date
            logger.info("Daily token usage reset")
        
        if self.daily_tokens_used >= self.settings.MAX_TOKENS * 0.95:  # 95% threshold
            raise LLMProcessingError("Approaching daily token limit")
    
    def _update_token_usage(self, tokens: int):
        """Enhanced token usage tracking."""
        self.daily_tokens_used += tokens
        
        # Progressive warnings
        usage_percentage = (self.daily_tokens_used / self.settings.MAX_TOKENS) * 100
        
        if usage_percentage > 90:
            logger.warning(f"High token usage: {usage_percentage:.1f}% ({self.daily_tokens_used}/{self.settings.MAX_TOKENS})")
        elif usage_percentage > 75:
            logger.info(f"Token usage: {usage_percentage:.1f}% ({self.daily_tokens_used}/{self.settings.MAX_TOKENS})")
    
    async def get_usage_stats(self) -> Dict:
        """Get comprehensive usage statistics."""
        current_time = time.time()
        requests_last_hour = len([
            req_time for req_time in self.request_times
            if current_time - req_time < 3600
        ])
        
        return {
            'daily_tokens_used': self.daily_tokens_used,
            'max_daily_tokens': self.settings.MAX_TOKENS,
            'token_usage_percentage': (self.daily_tokens_used / self.settings.MAX_TOKENS) * 100,
            'requests_last_minute': len(self.request_times),
            'requests_last_hour': requests_last_hour,
            'rate_limit_per_minute': self.rate_limit,
            'current_date': self.last_reset_date,
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'success_rate': ((self.request_count - self.error_count) / max(1, self.request_count)) * 100
        }
    
    async def health_check(self) -> Dict:
        """Perform health check of the LLM client."""
        try:
            # Simple test generation
            test_response = await self.generate_response(
                "Test query for health check", 
                query_type=QueryType.GENERAL,
                temperature=0.1
            )
            
            return {
                'status': 'healthy',
                'model': self.model_name,
                'response_time_ms': test_response.processing_time_ms,
                'tokens_available': self.settings.MAX_TOKENS - self.daily_tokens_used,
                'last_test': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_test': time.strftime("%Y-%m-%d %H:%M:%S")
            }
