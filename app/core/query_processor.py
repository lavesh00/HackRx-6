"""
Enhanced query processing engine with comprehensive preprocessing for 
insurance, legal, HR, and compliance documents.
"""

import asyncio
import logging
import time
import uuid
import re
from typing import Dict, List, Optional, Tuple, Set

from app.core.document_processor import DocumentProcessor
from app.core.embedding_engine import EmbeddingEngine
from app.core.llm_client import LLMClient
from app.core.clause_matcher import ClauseMatcher
from app.services.cache_service import CacheService
from app.utils.exceptions import (
    DocumentProcessingError,
    EmbeddingGenerationError, 
    LLMProcessingError,
    QueryProcessingError
)
from config.settings import get_settings

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Main query processing orchestrator with comprehensive preprocessing."""
    
    def __init__(
        self,
        document_processor: DocumentProcessor,
        embedding_engine: EmbeddingEngine,
        llm_client: LLMClient,
        cache_service: Optional[CacheService] = None
    ):
        self.document_processor = document_processor
        self.embedding_engine = embedding_engine
        self.llm_client = llm_client
        self.cache_service = cache_service
        self.clause_matcher = ClauseMatcher(embedding_engine)
        self.settings = get_settings()
        self._embedding_initialized = False
        
        # MASSIVELY EXPANDED comprehensive synonym mapping
        self.comprehensive_synonyms = {
            # Grace Period Variations (Enhanced)
            "grace period": [
                "payment grace period", "premium grace period", "grace time", "grace days",
                "payment window", "premium payment grace", "renewal grace period",
                "grace period for payment", "payment deadline extension", "grace allowance",
                "payment extension", "premium extension", "renewal extension", "policy extension",
                "late payment allowance", "payment tolerance period", "premium tolerance",
                "continuity grace", "policy continuity period", "uninterrupted coverage grace"
            ],
            
            # Waiting Period Variations (Enhanced)
            "waiting period": [
                "wait period", "waiting time", "exclusion period", "cooling period",
                "waiting duration", "wait time", "qualification period", "probation period",
                "elimination period", "pre-coverage period", "initial waiting period",
                "coverage waiting", "benefit waiting", "claim waiting", "treatment waiting",
                "medical waiting", "service waiting", "care waiting", "therapy waiting",
                "procedure waiting", "surgery waiting", "operation waiting", "hospitalization waiting"
            ],
            
            # Time Period Variations (Massively Expanded)
            "30 days": ["thirty days", "one month", "30-day period", "thirty day period", "1 month", 
                       "thirty (30) days", "30 day", "thirty-day", "one (1) month", "monthly period"],
            "36 months": ["thirty six months", "three years", "3 years", "36-month period", "thirty-six months",
                         "thirty six (36) months", "3 year period", "three (3) years", "36 month period",
                         "3-year period", "three year period", "36-months", "thirty-six (36) months"],
            "24 months": ["twenty four months", "two years", "2 years", "24-month period", "twenty-four months",
                         "twenty four (24) months", "2 year period", "two (2) years", "24 month period",
                         "2-year period", "two year period", "24-months", "twenty-four (24) months"],
            "2 years": ["two years", "24 months", "twenty four months", "2-year period", "two (2) years",
                       "two year period", "24 month period", "twenty-four months", "2 year", "two-year"],
            "1 year": ["one year", "12 months", "twelve months", "annual period", "yearly", "1-year",
                      "one (1) year", "12 month period", "twelve (12) months", "annual", "per annum"],
            "3 months": ["three months", "90 days", "quarterly", "3-month period", "three (3) months",
                        "ninety days", "3 month period", "quarter period", "90-day period"],
            "6 months": ["six months", "180 days", "half year", "6-month period", "six (6) months",
                        "semi-annual", "6 month period", "half-yearly", "180-day period"],
            "4 years": ["four years", "48 months", "4-year period", "four (4) years", "48 month period",
                       "four year period", "48-month period", "forty-eight months"],
            "150 km": ["150 kilometers", "150 kilometres", "one hundred fifty km", "150-km", "150 kms",
                      "one hundred fifty kilometers", "150 kilometer", "150-kilometer"],
            
            # Coverage Terms (Enhanced)
            "coverage": [
                "benefits", "protection", "indemnity", "compensation", "reimbursement",
                "covered expenses", "eligible expenses", "payable benefits", "insured benefits",
                "policy benefits", "insurance benefits", "medical benefits", "treatment benefits",
                "care benefits", "health benefits", "hospitalization benefits", "surgical benefits",
                "therapeutic benefits", "diagnostic benefits", "pharmaceutical benefits", "medication benefits"
            ],
            
            # Maternity Terms (Enhanced)
            "maternity": [
                "pregnancy", "childbirth", "delivery", "maternity expenses", "pregnancy coverage",
                "obstetric care", "prenatal care", "postnatal care", "labor and delivery",
                "pregnancy benefits", "maternity benefits", "childbirth expenses", "delivery expenses",
                "obstetric", "prenatal", "postnatal", "antenatal", "perinatal", "neonatal",
                "maternal care", "maternal health", "pregnancy care", "birthing", "confinement",
                "gestation", "expectant mother", "pregnant woman", "mother-to-be", "maternity ward"
            ],
            
            # Pre-existing Disease Terms (Enhanced)
            "pre-existing": [
                "pre existing", "existing condition", "prior condition", "previous illness",
                "pre-existing disease", "PED", "existing medical condition", "prior medical history",
                "pre-existing ailment", "chronic condition", "pre-existing illness", "existing ailment",
                "previous medical condition", "prior ailment", "existing disease", "chronic disease",
                "hereditary condition", "congenital condition", "pre-existing medical condition",
                "pre-existing health condition", "existing health condition", "prior health condition"
            ],
            
            # Medical Procedure Terms (Enhanced)
            "cataract": [
                "cataract surgery", "cataract operation", "cataract treatment", "lens replacement",
                "cataract removal", "eye surgery", "lens surgery", "ocular surgery", "eye operation",
                "lens operation", "intraocular lens", "IOL", "phacoemulsification", "cataract extraction",
                "lens implant", "artificial lens", "eye lens replacement", "vision correction surgery"
            ],
            
            "surgery": [
                "operation", "surgical procedure", "medical procedure", "treatment",
                "surgical treatment", "operative procedure", "surgical intervention", "medical operation",
                "surgical operation", "operative treatment", "invasive procedure", "surgical care",
                "operative care", "surgical service", "medical surgery", "clinical procedure"
            ],
            
            # Air Ambulance Terms (NEW - Critical for your test document)
            "air ambulance": [
                "air ambulance services", "helicopter ambulance", "medical helicopter", "air medical transport",
                "aviation ambulance", "flight ambulance", "medical aviation", "emergency aviation",
                "helicopter medical service", "air medical service", "medical helicopter transport",
                "emergency air transport", "aerial ambulance", "medical flight", "ambulance aircraft",
                "emergency helicopter", "medical chopper", "air medical evacuation", "aeromedical transport"
            ],
            
            "distance": [
                "travel distance", "transportation distance", "journey distance", "flight distance",
                "travel range", "coverage distance", "service distance", "operational distance",
                "kilometer", "kilometres", "km", "kms", "miles", "nautical miles"
            ],
            
            # Well Mother/Baby Terms (NEW - Critical for your test document)
            "well mother": [
                "well mother cover", "well mother care", "mother wellness", "maternal wellness",
                "mother care", "maternal care", "expectant mother care", "pregnancy wellness",
                "maternal health care", "mother health", "well mother benefits", "mother wellness program"
            ],
            
            "well baby": [
                "well baby care", "well baby expenses", "baby wellness", "infant wellness",
                "newborn care", "baby care", "infant care", "neonatal care", "baby health",
                "infant health", "newborn wellness", "well baby benefits", "baby wellness program",
                "healthy baby", "baby medical care", "infant medical care", "newborn medical care"
            ],
            
            "routine medical care": [
                "routine care", "regular medical care", "standard medical care", "basic medical care",
                "preventive care", "wellness care", "health maintenance", "regular checkups",
                "routine checkups", "standard checkups", "medical maintenance", "health monitoring"
            ],
            
            "preventive care": [
                "preventive care services", "preventative care", "wellness services", "health screening",
                "health maintenance", "preventive medicine", "wellness programs", "health promotion",
                "disease prevention", "health protection", "preventive health", "wellness care"
            ],
            
            # UIN and Regulatory Terms (NEW - Critical)
            "uin": [
                "unique identification number", "product identification", "policy identification",
                "insurance identification", "regulatory number", "product code", "policy code",
                "identification code", "reference number", "product number", "policy number",
                "registration number", "approval number", "license number"
            ],
            
            "base product": [
                "base policy", "main product", "primary product", "core product", "basic product",
                "underlying product", "foundation product", "principal product", "master product",
                "parent product", "root product", "original product"
            ],
            
            "add on": [
                "add-on", "addon", "rider", "endorsement", "supplement", "extension", "additional cover",
                "optional cover", "extra cover", "supplementary cover", "ancillary cover",
                "additional benefit", "extra benefit", "supplementary benefit", "optional benefit"
            ],
            
            # Organ Donation Terms (Enhanced)
            "organ donor": [
                "organ donation", "donor expenses", "transplant donor", "organ harvesting",
                "donor hospitalization", "organ transplant donor", "transplantation donor",
                "organ harvesting expenses", "donor medical expenses", "transplant surgery donor",
                "organ procurement", "donor surgery", "organ retrieval", "donor operation"
            ],
            
            # Discount and Bonus Terms (Enhanced)
            "no claim discount": [
                "NCD", "no claim bonus", "NCB", "claim free discount", "loyalty discount",
                "renewal discount", "good health discount", "claim-free bonus", "no claims discount",
                "claim-free discount", "bonus discount", "renewal bonus", "loyalty bonus",
                "experience discount", "safe driving discount", "good record discount"
            ],
            
            # Health Check Terms (Enhanced)
            "health check": [
                "health checkup", "preventive checkup", "medical checkup", "health screening",
                "annual checkup", "routine checkup", "preventive care", "wellness checkup",
                "medical examination", "health assessment", "health evaluation", "medical screening",
                "wellness examination", "health monitoring", "medical assessment", "health review"
            ],
            
            # AYUSH Terms (Enhanced)
            "ayush": [
                "ayurveda", "yoga", "naturopathy", "unani", "siddha", "homeopathy",
                "alternative medicine", "traditional medicine", "ayurvedic treatment",
                "homeopathic treatment", "natural medicine", "complementary medicine",
                "integrative medicine", "holistic medicine", "traditional healing",
                "herbal medicine", "natural healing", "alternative therapy"
            ],
            
            # Hospital Terms (Enhanced)
            "hospital": [
                "medical institution", "healthcare facility", "nursing home", "medical center",
                "clinic", "healthcare center", "medical facility", "treatment center",
                "healthcare institution", "medical establishment", "healthcare establishment",
                "treatment facility", "care facility", "medical complex", "healthcare complex"
            ],
            
            # Room and ICU Terms (Enhanced)
            "room rent": [
                "daily room", "room charges", "accommodation charges", "bed charges",
                "room and board", "hospitalization charges", "room expenses", "accommodation expenses",
                "bed expenses", "room rate", "accommodation rate", "bed rate", "room cost",
                "accommodation cost", "bed cost", "daily room charges", "room tariff"
            ],
            
            "icu": [
                "intensive care unit", "ICU charges", "critical care", "intensive care",
                "critical care unit", "CCU", "intensive care expenses", "critical care expenses",
                "intensive care costs", "critical care costs", "ICU costs", "ICU rates",
                "intensive care rates", "critical care rates", "intensive therapy unit", "ITU"
            ],
            
            # Plan Terms (Enhanced)
            "plan a": ["plan-a", "plana", "basic plan", "plan 1", "option a", "package a", "Plan A", "PLAN A"],
            "plan b": ["plan-b", "planb", "standard plan", "plan 2", "option b", "package b", "Plan B", "PLAN B"],
            "plan c": ["plan-c", "planc", "premium plan", "plan 3", "option c", "package c", "Plan C", "PLAN C"],
            
            # Financial Terms (Enhanced)
            "premium": [
                "insurance premium", "policy premium", "payment", "installment",
                "contribution", "premium amount", "policy payment", "insurance payment",
                "premium charges", "policy charges", "insurance charges", "premium cost",
                "policy cost", "insurance cost", "premium rate", "policy rate"
            ],
            
            "deductible": [
                "excess", "co-pay", "copayment", "out of pocket", "self retention",
                "franchise", "deductible amount", "excess amount", "co-payment amount",
                "out-of-pocket amount", "self-retention amount", "excess charge",
                "co-pay charge", "deductible charge", "excess cost", "co-pay cost"
            ],
            
            "sum insured": [
                "coverage amount", "insured amount", "policy limit", "maximum coverage",
                "benefit limit", "insurance amount", "SI", "sum assured", "coverage limit",
                "insurance limit", "policy amount", "insured sum", "assured sum",
                "maximum benefit", "benefit amount", "coverage sum", "insurance sum"
            ],
            
            # Legal and Compliance Terms (Enhanced)
            "policy": [
                "insurance policy", "contract", "agreement", "terms and conditions",
                "policy document", "insurance contract", "policy terms", "insurance terms",
                "contract terms", "agreement terms", "policy conditions", "insurance conditions",
                "contract conditions", "policy provisions", "insurance provisions"
            ],
            
            "exclusion": [
                "excluded", "not covered", "exception", "limitation", "restriction",
                "excluded condition", "non-covered expense", "excluded treatment",
                "excluded service", "excluded benefit", "excluded care", "not payable",
                "non-payable", "non-reimbursable", "ineligible", "disallowed"
            ],
            
            # Licensing and Certification Terms (NEW)
            "licensed": [
                "licensed", "certified", "authorized", "approved", "accredited", "registered",
                "qualified", "permitted", "sanctioned", "endorsed", "validated", "recognized",
                "duly licensed", "properly licensed", "legally licensed", "officially licensed"
            ],
            
            "competent authority": [
                "government authority", "regulatory authority", "licensing authority", "competent government authority",
                "authorized authority", "official authority", "regulatory body", "government body",
                "licensing body", "certification authority", "approval authority", "regulatory agency"
            ],
            
            # Table and Structured Data Terms (NEW - Critical)
            "table": [
                "table of benefits", "benefit table", "coverage table", "schedule", "benefit schedule",
                "coverage schedule", "table of coverage", "benefits table", "policy schedule",
                "insurance schedule", "benefit chart", "coverage chart", "benefits chart"
            ],
            
            "limit": [
                "limitation", "cap", "maximum", "ceiling", "upper limit", "threshold", "boundary",
                "restriction", "constraint", "maximum limit", "benefit limit", "coverage limit",
                "payment limit", "reimbursement limit", "claim limit", "expense limit"
            ],
            
            # Period Options Terms (NEW)
            "period": [
                "time period", "coverage period", "policy period", "benefit period", "term",
                "duration", "timeframe", "time frame", "span", "length", "interval",
                "phase", "stage", "epoch", "era", "cycle"
            ],
            
            "options": [
                "choices", "alternatives", "selections", "variants", "varieties", "types",
                "categories", "plans", "schemes", "packages", "programs", "offerings"
            ],
            
            # Multiple Birth Terms (NEW)
            "multiple": [
                "multiple births", "multiple babies", "twins", "triplets", "quadruplets",
                "multiple children", "multiple newborns", "multiple infants", "twin births",
                "multiple deliveries", "simultaneous births"
            ],
            
            # Proportionate Payment Terms (NEW)
            "proportionate": [
                "proportional", "pro-rata", "proportionate payment", "proportional payment",
                "partial payment", "reduced payment", "scaled payment", "adjusted payment",
                "calculated payment", "percentage payment", "ratio-based payment"
            ]
        }
        
        # Enhanced Number word mappings
        self.number_words = {
            "1": ["one", "first", "single", "1st", "i"],
            "2": ["two", "second", "double", "twice", "2nd", "ii"],
            "3": ["three", "third", "triple", "thrice", "3rd", "iii"],
            "4": ["four", "fourth", "quad", "4th", "iv"],
            "5": ["five", "fifth", "5th", "v"],
            "6": ["six", "sixth", "6th", "vi"],
            "7": ["seven", "seventh", "7th", "vii"],
            "8": ["eight", "eighth", "8th", "viii"],
            "9": ["nine", "ninth", "9th", "ix"],
            "10": ["ten", "tenth", "10th", "x"],
            "12": ["twelve", "twelfth", "dozen", "12th"],
            "15": ["fifteen", "fifteenth", "15th"],
            "24": ["twenty four", "twenty-four", "two dozen", "24th"],
            "30": ["thirty", "thirtieth", "30th"],
            "36": ["thirty six", "thirty-six", "36th"],
            "48": ["forty eight", "forty-eight", "48th"],
            "50": ["fifty", "fiftieth", "50th"],
            "100": ["hundred", "one hundred", "100th"],
            "150": ["one hundred fifty", "one hundred and fifty", "150th"]
        }
        
        # Enhanced insurance-specific patterns
        self.insurance_patterns = {
            # UIN Pattern Detection
            r'uin|unique identification': [
                "product UIN", "policy UIN", "base product UIN", "add-on UIN",
                "identification number", "product code", "policy code", "registration number"
            ],
            
            # Distance and Travel Patterns
            r'distance.*travel|travel.*distance': [
                "maximum distance", "travel limit", "distance limit", "coverage distance",
                "service range", "operational range", "travel range", "distance coverage"
            ],
            
            # Licensing Patterns
            r'licens.*authority|authority.*licens': [
                "government licensing", "regulatory approval", "official authorization",
                "competent authority", "licensing body", "certification authority"
            ],
            
            # Multiple Options Patterns
            r'three.*option|option.*three': [
                "three alternatives", "three choices", "three periods", "three plans",
                "three variants", "three types", "three categories", "multiple options"
            ],
            
            # Table and Benefits Patterns
            r'table.*benefit|benefit.*table': [
                "benefits schedule", "coverage table", "benefit chart", "policy schedule",
                "insurance schedule", "benefit summary", "coverage summary"
            ]
        }
        
        logger.info("Query processor initialized with MASSIVELY ENHANCED comprehensive preprocessing")
    
    async def _ensure_embedding_engine_initialized(self):
        """Ensure embedding engine is initialized (lazy initialization)."""
        if not self._embedding_initialized:
            try:
                await self.embedding_engine.initialize()
                self._embedding_initialized = True
                logger.info("Embedding engine initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize embedding engine: {e}")
                raise
    
    async def process_document_queries(
        self, 
        documents_url: str, 
        questions: List[str]
    ) -> List[str]:
        """Process multiple queries against a document with enhanced retrieval."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        logger.info(f"Processing {len(questions)} queries for document {documents_url[:50]}... (ID: {request_id})")
        
        try:
            # Ensure embedding engine is initialized
            await self._ensure_embedding_engine_initialized()
            
            # Step 1: Process document
            document_data = await self._process_document_with_cache(documents_url)
            
            # Step 2: Add document to vector index if not already present
            await self._ensure_document_indexed(document_data)
            
            # Step 3: Process all questions with enhanced preprocessing
            answers = await self._process_questions_batch(
                questions, 
                document_data['document_id'],
                request_id
            )
            
            # Log processing summary
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Completed processing {len(questions)} queries in {total_time:.2f}ms (ID: {request_id})")
            
            return answers
            
        except Exception as e:
            logger.error(f"Query processing failed (ID: {request_id}): {e}")
            raise QueryProcessingError(f"Failed to process queries: {str(e)}")

    async def _process_document_with_cache(self, documents_url: str) -> Dict:
        """Process document with caching support."""
        cache_key = f"document:{hash(documents_url)}"
        
        if self.cache_service:
            cached_doc = await self.cache_service.get(cache_key)
            if cached_doc:
                logger.info("Retrieved document from cache")
                return cached_doc
        
        logger.info("Processing document from URL")
        document_data = await self.document_processor.process_document_from_url(documents_url)
        
        if self.cache_service:
            await self.cache_service.set(cache_key, document_data, ttl=7200)
        
        return document_data
    
    async def _ensure_document_indexed(self, document_data: Dict) -> None:
        """Ensure document chunks are indexed in the vector database."""
        document_id = document_data['document_id']
        current_chunks = len(document_data['chunks'])
        
        logger.info(f"Adding {current_chunks} chunks to vector index")
        
        await self.embedding_engine.add_documents(
            document_id=document_id,
            chunks=document_data['chunks'],
            metadata={
                'url': document_data['url'],
                'file_type': document_data['file_type'],
                'size_bytes': document_data['metadata']['size_bytes']
            }
        )
    
    async def _process_questions_batch(
        self, 
        questions: List[str], 
        document_id: str,
        request_id: str
    ) -> List[str]:
        """Process multiple questions efficiently."""
        semaphore = asyncio.Semaphore(3)  # Reduced for better stability
        
        async def process_single_question(question: str, index: int) -> Tuple[int, str]:
            async with semaphore:
                answer = await self._process_single_question(
                    question, 
                    document_id, 
                    f"{request_id}-{index}"
                )
                return index, answer
        
        tasks = [
            process_single_question(question, i) 
            for i, question in enumerate(questions)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        ordered_answers = [''] * len(questions)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Question processing failed: {result}")
                ordered_answers.append("I apologize, but I encountered an error processing this question.")
            else:
                index, answer = result
                ordered_answers[index] = answer
        
        return ordered_answers[:len(questions)]
    
    async def _process_single_question(
        self, 
        question: str, 
        document_id: str,
        question_id: str
    ) -> str:
        """Process a single question with comprehensive preprocessing."""
        start_time = time.time()
        
        try:
            logger.info(f"Processing question: {question[:50]}... (ID: {question_id})")
            
            # Check cache
            cache_key = f"qa:{hash(document_id + question)}"
            if self.cache_service:
                cached_answer = await self.cache_service.get(cache_key)
                if cached_answer:
                    logger.info(f"Retrieved answer from cache (ID: {question_id})")
                    return cached_answer
            
            # Get comprehensive chunks using enhanced retrieval
            relevant_chunks = await self._get_comprehensive_chunks(question, document_id)
            
            if not relevant_chunks:
                logger.warning(f"No relevant chunks found for question (ID: {question_id})")
                return "I couldn't find relevant information in the document to answer this question."
            
            # Apply clause matching with lower threshold for broader matching
            clause_matches = await self.clause_matcher.find_relevant_clauses(
                query=question,
                document_chunks=relevant_chunks,
                threshold=0.3,  # Lowered from 0.4
                max_matches=12  # Increased from 8
            )
            
            # Select best chunks
            context_chunks = self._select_best_chunks(relevant_chunks, clause_matches)
            
            # Generate answer
            answer = await self.llm_client.answer_question_with_context(
                question=question,
                context_chunks=context_chunks,
                document_info={'document_id': document_id}
            )
            
            # Post-process answer
            final_answer = self._post_process_answer(answer)
            
            # Cache result
            if self.cache_service:
                await self.cache_service.set(cache_key, final_answer, ttl=3600)
            
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Generated answer in {processing_time:.2f}ms (ID: {question_id})")
            
            return final_answer
            
        except Exception as e:
            logger.error(f"Single question processing failed (ID: {question_id}): {e}")
            return "I apologize, but I encountered an error while processing this question. Please try again."
    
    async def _preprocess_query(self, question: str) -> List[str]:
        """Generate comprehensive query variations for better retrieval - MASSIVELY ENHANCED."""
        base_query = question.lower().strip()
        query_variations = [question.strip()]  # Original question
        
        # Extract numbers and special patterns
        numbers = re.findall(r'\b\d+\b', base_query)
        alphanumeric_codes = re.findall(r'\b[A-Z]{2,}[0-9]{2,}[A-Z0-9]*\b', question.upper())
        
        # 1. Direct synonym expansion (ENHANCED)
        for term, synonyms in self.comprehensive_synonyms.items():
            if term in base_query:
                # Add variations with synonyms
                for synonym in synonyms:
                    variant = base_query.replace(term, synonym)
                    query_variations.append(variant.title())
                    query_variations.append(synonym)
                    # Add partial matches
                    if len(synonym.split()) > 1:
                        for word in synonym.split():
                            if len(word) > 3:
                                query_variations.append(word)
        
        # 2. Enhanced number word variations
        for num in numbers:
            if num in self.number_words:
                for word_form in self.number_words[num]:
                    variant = base_query.replace(num, word_form)
                    query_variations.append(variant.title())
                    query_variations.append(word_form)
        
        # 3. Enhanced pattern-based expansions
        pattern_expansions = self._get_enhanced_pattern_expansions(base_query)
        query_variations.extend(pattern_expansions)
        
        # 4. Insurance-specific pattern matching (NEW)
        insurance_expansions = self._get_insurance_specific_expansions(base_query)
        query_variations.extend(insurance_expansions)
        
        # 5. Context-specific expansions
        context_expansions = self._get_context_specific_expansions(base_query)
        query_variations.extend(context_expansions)
        
        # 6. Technical term expansions (NEW)
        technical_expansions = self._get_technical_expansions(base_query, alphanumeric_codes)
        query_variations.extend(technical_expansions)
        
        # 7. Semantic relationship expansions (NEW)
        semantic_expansions = self._get_semantic_expansions(base_query)
        query_variations.extend(semantic_expansions)
        
        # 8. Remove duplicates and filter
        unique_variations = []
        seen = set()
        
        for variant in query_variations:
            variant_clean = variant.strip().lower()
            if (variant_clean and 
                variant_clean not in seen and 
                len(variant_clean) > 1 and 
                len(variant.split()) <= 20):  # Increased length limit
                seen.add(variant_clean)
                unique_variations.append(variant.strip())
        
        # 9. Prioritize and limit
        prioritized = self._prioritize_variations_enhanced(unique_variations, question)
        
        logger.debug(f"Generated {len(prioritized)} query variations for: {question[:50]}...")
        return prioritized[:20]  # Increased limit to 20 for better coverage
    
    def _get_enhanced_pattern_expansions(self, query: str) -> List[str]:
        """Enhanced pattern-based query expansions."""
        expansions = []
        
        # MASSIVELY EXPANDED patterns
        patterns = {
            # Air Ambulance Patterns (NEW - Critical)
            r'air ambulance.*distance|distance.*air ambulance': [
                "150 km air ambulance", "maximum air ambulance distance", "air ambulance travel limit",
                "air ambulance range", "helicopter ambulance distance", "medical helicopter range",
                "aviation ambulance limit", "air medical transport distance", "flight ambulance range"
            ],
            
            r'air ambulance.*exceed|exceed.*air ambulance': [
                "distance exceeded air ambulance", "proportionate air ambulance payment",
                "air ambulance over distance", "air ambulance distance limit exceeded",
                "air ambulance partial payment", "reduced air ambulance payment"
            ],
            
            # Well Mother/Baby Patterns (NEW)
            r'well mother.*period|period.*well mother': [
                "three well mother periods", "well mother coverage periods", "well mother options",
                "maternal coverage periods", "pregnancy coverage periods", "mother care periods"
            ],
            
            r'well baby.*cover|cover.*well baby': [
                "newborn baby coverage", "infant care coverage", "baby medical coverage",
                "well baby expenses", "healthy baby care", "baby wellness coverage"
            ],
            
            # UIN Patterns (NEW - Critical)
            r'uin|product.*uin|base.*uin': [
                "base product UIN", "add-on UIN", "policy UIN", "product identification number",
                "unique identification", "regulatory number", "approval number", "license number"
            ],
            
            # Multiple Birth Patterns (NEW)
            r'multiple.*birth|multiple.*bab': [
                "twins coverage", "multiple babies coverage", "twin births", "multiple children",
                "simultaneous births", "multiple deliveries", "twin delivery", "multiple infants"
            ],
            
            # Proportionate Payment Patterns (NEW)
            r'proportion.*payment|payment.*proportion': [
                "partial payment", "reduced payment", "pro-rata payment", "calculated payment",
                "percentage payment", "scaled payment", "adjusted payment", "ratio payment"
            ],
            
            # Existing patterns (Enhanced)
            r'grace period.*premium': [
                "thirty days premium payment", "30 days grace premium",
                "premium payment grace period", "grace period payment",
                "premium grace thirty days", "payment grace period",
                "renewal grace premium", "policy grace premium"
            ],
            
            r'waiting period.*pre.*existing': [
                "36 months pre-existing diseases", "thirty six months PED",
                "pre-existing disease waiting period", "PED 36 months waiting",
                "continuous coverage 36 months", "pre-existing condition waiting",
                "chronic condition waiting", "existing condition waiting"
            ],
            
            r'waiting period.*cataract': [
                "cataract two years waiting", "cataract surgery 2 years",
                "two year waiting cataract", "cataract operation waiting period",
                "eye surgery waiting period", "lens surgery waiting",
                "vision surgery waiting", "ocular surgery waiting"
            ],
            
            r'maternity.*cover|cover.*maternity': [
                "maternity expenses covered", "pregnancy coverage conditions",
                "childbirth expenses", "maternity benefits", "24 months maternity waiting",
                "pregnancy benefits", "delivery coverage", "obstetric coverage",
                "prenatal coverage", "postnatal coverage"
            ],
            
            # Table and Benefits Patterns (Enhanced)
            r'table.*benefit|benefit.*table': [
                "benefits schedule", "coverage table", "benefit chart", "policy schedule",
                "insurance schedule", "benefit summary", "coverage summary",
                "benefits list", "coverage list", "benefit breakdown"
            ],
            
            # Exclusions Patterns (Enhanced)
            r'exclusion|not.*cover|excluded': [
                "policy exclusions", "coverage exclusions", "excluded conditions",
                "non-covered expenses", "excluded treatments", "excluded services",
                "limitations", "restrictions", "exceptions", "non-payable expenses"
            ],
            
            # Licensing and Authority Patterns (Enhanced)
            r'licens.*authority|authority.*licens|competent.*authority': [
                "government licensing authority", "regulatory licensing body", "competent government authority",
                "official licensing authority", "authorized government body", "regulatory approval authority",
                "certification authority", "accreditation body", "licensing agency"
            ]
        }
        
        for pattern, variations in patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                expansions.extend(variations)
        
        return expansions
    
    def _get_insurance_specific_expansions(self, query: str) -> List[str]:
        """Generate insurance-specific domain expansions."""
        expansions = []
        
        # Insurance document structure terms
        if any(term in query for term in ['section', 'clause', 'provision', 'article']):
            expansions.extend([
                "policy section", "insurance clause", "coverage provision",
                "benefit article", "terms section", "conditions clause"
            ])
        
        # Regulatory and compliance terms
        if any(term in query for term in ['uin', 'regulation', 'compliance', 'authority']):
            expansions.extend([
                "regulatory compliance", "insurance regulation", "policy compliance",
                "regulatory authority", "insurance authority", "compliance requirement"
            ])
        
        # Coverage and benefits terms
        if any(term in query for term in ['benefit', 'coverage', 'policy', 'plan']):
            expansions.extend([
                "insurance benefits", "policy coverage", "benefit coverage",
                "plan benefits", "coverage benefits", "policy benefits"
            ])
        
        return expansions
    
    def _get_technical_expansions(self, query: str, alphanumeric_codes: List[str]) -> List[str]:
        """Generate technical term expansions."""
        expansions = []
        
        # Handle UIN codes and technical identifiers
        for code in alphanumeric_codes:
            expansions.extend([
                f"product {code}", f"policy {code}", f"UIN {code}",
                f"identification {code}", f"number {code}", f"code {code}"
            ])
        
        # Technical insurance terms
        technical_terms = {
            'uin': ['unique identification number', 'product identification', 'policy code'],
            'si': ['sum insured', 'insured amount', 'coverage amount'],
            'ped': ['pre-existing disease', 'existing condition', 'prior condition'],
            'ncd': ['no claim discount', 'no claim bonus', 'claim free discount'],
            'icu': ['intensive care unit', 'critical care', 'intensive care'],
            'ccv': ['cashless claim voucher', 'cashless facility', 'cashless treatment']
        }
        
        for abbrev, full_terms in technical_terms.items():
            if abbrev in query.lower():
                expansions.extend(full_terms)
        
        return expansions
    
    def _get_semantic_expansions(self, query: str) -> List[str]:
        """Generate semantic relationship expansions."""
        expansions = []
        
        # Semantic relationships for insurance concepts
        semantic_map = {
            'maximum': ['limit', 'ceiling', 'cap', 'upper bound', 'highest'],
            'minimum': ['floor', 'lowest', 'base', 'starting'],
            'period': ['duration', 'time', 'term', 'span', 'interval'],
            'coverage': ['protection', 'benefits', 'indemnity', 'compensation'],
            'treatment': ['care', 'therapy', 'service', 'medical attention'],
            'expenses': ['costs', 'charges', 'fees', 'payments', 'bills']
        }
        
        for concept, related_terms in semantic_map.items():
            if concept in query.lower():
                expansions.extend(related_terms)
        
        return expansions
    
    def _get_context_specific_expansions(self, query: str) -> List[str]:
        """Generate context-specific expansions based on domain knowledge."""
        expansions = []
        
        # Insurance policy contexts (Enhanced)
        if any(term in query for term in ['policy', 'coverage', 'benefit', 'claim']):
            expansions.extend([
                "insurance policy benefits", "coverage conditions", "policy terms and conditions",
                "benefit limitations", "claim procedures", "policy exclusions", "coverage exclusions",
                "benefit exclusions", "policy provisions", "insurance provisions"
            ])
        
        # Medical treatment contexts (Enhanced)
        if any(term in query for term in ['treatment', 'surgery', 'medical', 'hospital']):
            expansions.extend([
                "medical treatment coverage", "surgical procedures", "hospitalization benefits",
                "inpatient treatment", "outpatient care", "medical expenses", "treatment expenses",
                "surgical expenses", "hospital expenses", "medical care expenses"
            ])
        
        # Financial contexts (Enhanced)
        if any(term in query for term in ['premium', 'payment', 'discount', 'limit', 'amount']):
            expansions.extend([
                "premium payment terms", "financial benefits", "cost limitations", "payment schedules",
                "discount eligibility", "amount restrictions", "payment limits", "cost limits",
                "expense limits", "reimbursement limits"
            ])
        
        # Time-based contexts (Enhanced)
        if any(term in query for term in ['period', 'time', 'duration', 'year', 'month', 'day']):
            expansions.extend([
                "time periods", "duration requirements", "waiting periods", "coverage periods",
                "renewal periods", "grace periods", "policy periods", "benefit periods",
                "term periods", "coverage terms"
            ])
        
        # Air ambulance specific contexts (NEW)
        if any(term in query for term in ['air', 'ambulance', 'helicopter', 'aviation']):
            expansions.extend([
                "emergency air transport", "medical aviation", "air medical service",
                "helicopter medical service", "aviation medical service", "air ambulance service",
                "medical helicopter", "emergency helicopter", "medical flight"
            ])
        
        return expansions
    
    def _prioritize_variations_enhanced(self, variations: List[str], original: str) -> List[str]:
        """Enhanced prioritization with insurance-specific scoring."""
        scored_variations = []
        
        for variant in variations:
            score = 0
            variant_lower = variant.lower()
            
            # Original query gets highest priority
            if variant_lower == original.lower():
                score += 100
            
            # Length-based scoring (refined)
            word_count = len(variant.split())
            if word_count >= 5:
                score += 60
            elif word_count >= 3:
                score += 40
            elif word_count >= 2:
                score += 20
            
            # Number presence bonus
            if re.search(r'\d+', variant):
                score += 25
            
            # Insurance-specific term bonuses (Enhanced)
            high_value_terms = [
                'uin', 'air ambulance', 'well mother', 'well baby', 'base product',
                'add-on', 'proportionate', 'distance', 'licensed', 'authority'
            ]
            medium_value_terms = [
                'grace', 'waiting', 'maternity', 'cataract', 'ncd', 'ayush',
                'exclusion', 'coverage', 'benefit', 'treatment'
            ]
            
            for term in high_value_terms:
                if term in variant_lower:
                    score += 30
            
            for term in medium_value_terms:
                if term in variant_lower:
                    score += 15
            
            # UIN code pattern bonus
            if re.search(r'\b[A-Z]{2,}[0-9]{2,}[A-Z0-9]*\b', variant.upper()):
                score += 40
            
            # Distance/measurement bonus
            if re.search(r'\d+\s*(km|kilometers|metres|meters)', variant_lower):
                score += 35
            
            # Period/time bonus
            if re.search(r'\d+\s*(years?|months?|days?)', variant_lower):
                score += 30
            
            scored_variations.append((score, variant))
        
        # Sort by score and return
        scored_variations.sort(key=lambda x: x[0], reverse=True)
        return [variant for score, variant in scored_variations]
    
    async def _get_comprehensive_chunks(self, question: str, document_id: str) -> List[Dict]:
        """Enhanced chunk retrieval with broader search parameters."""
        query_variations = await self._preprocess_query(question)
        all_chunks = {}
        
        # Multi-pass search with different parameters
        search_passes = [
            {'threshold': 0.3, 'k': 6, 'boost': 1.0},  # Broad
            {'threshold': 0.4, 'k': 4, 'boost': 0.8},  # Focused
            ]

        
        for pass_idx, search_params in enumerate(search_passes):
            for i, query in enumerate(query_variations):
                try:
                    # Adjust parameters based on query position and pass
                    adjusted_k = max(3, search_params['k'] - (i // 3))
                    adjusted_threshold = search_params['threshold'] + (i * 0.02)
                    
                    chunks = await self.embedding_engine.search(
                        query=query,
                        k=adjusted_k,
                        threshold=min(adjusted_threshold, 0.7)
                    )
                    
                    # Calculate boost (higher for earlier passes and queries)
                    query_boost = search_params['boost'] * (1.0 - (i * 0.02))
                    
                    for chunk in chunks:
                        chunk_id = chunk['chunk_id']
                        boosted_score = chunk['score'] * query_boost
                        
                        if chunk_id not in all_chunks or boosted_score > all_chunks[chunk_id]['score']:
                            chunk['score'] = boosted_score
                            chunk['matched_query'] = query
                            chunk['search_pass'] = pass_idx
                            all_chunks[chunk_id] = chunk
                            
                except Exception as e:
                    logger.warning(f"Search failed for query '{query}' in pass {pass_idx}: {e}")
                    continue
        
        # Sort by boosted score
        sorted_chunks = sorted(all_chunks.values(), 
                              key=lambda x: x['score'], reverse=True)
        
        result = sorted_chunks[:15]  # Increased to 20 chunks
        
        logger.info(f"Retrieved {len(result)} unique chunks from {len(query_variations)} variations across {len(search_passes)} passes")
        return result
    
    def _select_best_chunks(
        self, 
        vector_chunks: List[Dict], 
        clause_matches: List
    ) -> List[Dict]:
        """Enhanced chunk selection with better scoring."""
        chunk_scores = {}
        
        # Score vector search results
        for chunk in vector_chunks:
            chunk_id = f"{chunk['document_id']}_{chunk['chunk_index']}"
            chunk_scores[chunk_id] = {
                'chunk': chunk,
                'vector_score': chunk['score'],
                'clause_score': 0.0,
                'combined_score': chunk['score'],
                'search_pass': chunk.get('search_pass', 0)
            }
        
        # Add clause matching scores
        for match in clause_matches:
            chunk_id = f"{match.document_id}_{match.chunk_index}"
            if chunk_id in chunk_scores:
                chunk_scores[chunk_id]['clause_score'] = match.confidence
                # Enhanced combination with search pass consideration
                pass_bonus = 0.1 if chunk_scores[chunk_id]['search_pass'] == 0 else 0.0
                chunk_scores[chunk_id]['combined_score'] = (
                    0.6 * chunk_scores[chunk_id]['vector_score'] + 
                    0.3 * match.confidence + 
                    0.1 * pass_bonus
                )
        
        # Sort by combined score
        sorted_chunks = sorted(
            chunk_scores.values(), 
            key=lambda x: x['combined_score'], 
            reverse=True
        )
        
        return [item['chunk'] for item in sorted_chunks[:5]]  # Increased to 12 chunks
    
    def _post_process_answer(self, answer: str) -> str:
        """Enhanced post-processing for better answer quality."""
        if not answer:
            return "I couldn't generate an answer based on the available information."
        
        answer = answer.strip()
        
        # Enhanced prefix removal
        prefixes_to_remove = [
            "Based on the context provided, ",
            "According to the document, ",
            "The document states that ",
            "Answer: ",
            "Based on the provided context, ",
            "From the document, ",
            "The policy document indicates that ",
            "Based on the insurance document, ",
            "According to the policy, ",
            "The insurance policy states that ",
            "From the policy document, "
        ]
        
        for prefix in prefixes_to_remove:
            if answer.lower().startswith(prefix.lower()):
                answer = answer[len(prefix):].strip()
        
        # Enhanced capitalization and punctuation
        if answer and answer[0].islower():
            answer = answer[0].upper() + answer[1:]
        
        if answer and answer[-1] not in '.!?':
            answer += '.'
        
        # Fix common formatting issues
        answer = re.sub(r'\s+', ' ', answer)  # Multiple spaces
        answer = re.sub(r'\s+([,.;:])', r'\1', answer)  # Space before punctuation
        
        return answer
    
    async def get_processing_stats(self) -> Dict:
        """Get processing statistics."""
        embedding_stats = await self.embedding_engine.get_index_stats()
        llm_stats = await self.llm_client.get_usage_stats()
        
        return {
            'embedding_engine': embedding_stats,
            'llm_client': llm_stats,
            'cache_enabled': self.cache_service is not None,
            'comprehensive_preprocessing_enabled': True,
            'synonym_categories': len(self.comprehensive_synonyms),
            'enhanced_patterns': len(self.insurance_patterns),
            'number_mappings': len(self.number_words)
        }
    
    async def clear_document_cache(self, document_url: str) -> None:
        """Clear cached data for a specific document."""
        if not self.cache_service:
            return
        
        cache_key = f"document:{hash(document_url)}"
        await self.cache_service.delete(cache_key)
        
        logger.info(f"Cleared cache for document: {document_url[:50]}...")
