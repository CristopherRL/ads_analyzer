# === File: src/utils/cost_calculator.py ===

from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.database import get_db
from src.models import ModelPricing, ModelMapping
from src.logging_config import get_logger

logger = get_logger(__name__)

class CostCalculator:
    """
    Utility class for calculating LLM usage costs based on token consumption.
    """
    
    @staticmethod
    def get_generic_model_name(assigned_model_name: str) -> str:
        """
        Get the generic model name from assigned model name using model mappings.
        
        Args:
            assigned_model_name: The assigned model name (e.g., 'gpt-4o_analyst')
            
        Returns:
            Generic model name for pricing lookup, or the original name if no mapping found
        """
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            # Look for active mapping
            mapping = db.query(ModelMapping).filter(
                and_(
                    ModelMapping.assigned_model_name == assigned_model_name,
                    ModelMapping.is_active == True
                )
            ).first()
            
            if mapping:
                logger.info(f"Mapped {assigned_model_name} -> {mapping.generic_model_name}")
                return mapping.generic_model_name
            else:
                logger.warning(f"No mapping found for {assigned_model_name}, using original name")
                return assigned_model_name
                
        except Exception as e:
            logger.error(f"Error getting generic model name: {e}")
            return assigned_model_name
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def get_model_pricing(model_name: str, effective_date: Optional[datetime] = None) -> Optional[Dict[str, Decimal]]:
        """
        Get pricing information for a specific model.
        
        Args:
            model_name: Name of the model (e.g., 'gpt-4-turbo')
            effective_date: Date to get pricing for (defaults to current date)
            
        Returns:
            Dictionary with input_cost_per_1k_tokens and output_cost_per_1k_tokens, or None if not found
        """
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            if effective_date is None:
                effective_date = datetime.now().date()
            
            # Try to get specific model pricing first
            pricing = db.query(ModelPricing).filter(
                and_(
                    ModelPricing.model_name == model_name,
                    ModelPricing.effective_date <= effective_date
                )
            ).order_by(ModelPricing.effective_date.desc()).first()
            
            # If not found, try default pricing
            if not pricing:
                pricing = db.query(ModelPricing).filter(
                    and_(
                        ModelPricing.model_name == 'default',
                        ModelPricing.effective_date <= effective_date
                    )
                ).order_by(ModelPricing.effective_date.desc()).first()
            
            if pricing:
                return {
                    'input_cost_per_1k_tokens': pricing.input_cost_per_1k_tokens,
                    'output_cost_per_1k_tokens': pricing.output_cost_per_1k_tokens
                }
            else:
                logger.warning(f"No pricing found for model {model_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting model pricing: {e}")
            return None
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def calculate_cost(
        input_tokens: int, 
        output_tokens: int, 
        model_name: str = 'default'
    ) -> Optional[Decimal]:
        """
        Calculate the cost of LLM usage based on token consumption.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            model_name: Name of the model used (assigned or generic)
            
        Returns:
            Total cost in USD, or None if calculation fails
        """
        try:
            # First try to get generic model name if it's an assigned name
            generic_model_name = CostCalculator.get_generic_model_name(model_name)
            
            # Get pricing for the generic model name
            pricing = CostCalculator.get_model_pricing(generic_model_name)
            
            if not pricing:
                logger.warning(f"Could not calculate cost for model {model_name} (generic: {generic_model_name})")
                return None
            
            # Calculate costs (convert to Decimal for proper calculation)
            input_cost = Decimal(input_tokens) / Decimal(1000) * pricing['input_cost_per_1k_tokens']
            output_cost = Decimal(output_tokens) / Decimal(1000) * pricing['output_cost_per_1k_tokens']
            
            total_cost = input_cost + output_cost
            
            logger.info(f"Cost calculation for {model_name} -> {generic_model_name}: {input_tokens} input + {output_tokens} output tokens = ${total_cost:.6f}")
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return None
    
    @staticmethod
    def calculate_cost_with_mapping(
        input_tokens: int, 
        output_tokens: int, 
        assigned_model_name: str
    ) -> Optional[Decimal]:
        """
        Calculate cost using model mapping (explicit method for clarity).
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            assigned_model_name: The assigned model name (e.g., 'gpt-4o_analyst')
            
        Returns:
            Total cost in USD, or None if calculation fails
        """
        return CostCalculator.calculate_cost(input_tokens, output_tokens, assigned_model_name)
    
    @staticmethod
    def estimate_tokens_from_text(text: str) -> int:
        """
        Estimate token count from text (rough approximation).
        This is a simple estimation - for production, consider using tiktoken library.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Rough estimation: 1 token ≈ 4 characters for English text
        # This is a simplified approach - actual tokenization varies by model
        estimated_tokens = len(text) // 4
        
        # Minimum of 1 token for non-empty text
        return max(1, estimated_tokens)
    
    @staticmethod
    def get_llm_params_dict(
        model_name: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a dictionary of LLM parameters for storage.
        
        Args:
            model_name: Name of the model
            temperature: Temperature setting
            max_tokens: Maximum tokens setting
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of LLM parameters
        """
        params = {
            'model_name': model_name,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        # Add any additional parameters
        params.update(kwargs)
        
        return params
