import os
import fitz  # PyMuPDF
import logging
from typing import List, Tuple, Optional, Callable, Dict
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import json
from .main import Loader, BasePDFLoader
from open_webui.config import UPLOAD_DIR
from PIL import Image
import io
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import hashlib

log = logging.getLogger(__name__)

# Load OpenAI configuration
with open('/home/adminsiyu/code/nnit-chat-chromadb/vector_code/config.json', 'r') as f:
    config_data = json.load(f)

openai_api_key = config_data['api_key_ada3']
azure_endpoint = config_data['azure_endpoint_ada3']
openai_api_version = config_data['openai_api_version']
model_name_emdedding = config_data['model_name_emdedding_ada3']
model_name_gpt = config_data['model_name_gpt35_ada3']
model_name_gpt_4o = config_data['model_name_4o']
model_temperature = config_data['temperature']

# Initialize Azure OpenAI LLM
llm = AzureChatOpenAI(
    temperature=model_temperature,
    openai_api_key=openai_api_key,
    azure_endpoint=azure_endpoint,
    openai_api_version=openai_api_version,
    deployment_name=model_name_gpt_4o
)

class PDFProcessError(Exception):
    """PDF处理过程中的错误"""
    pass

class ImageProcessingError(PDFProcessError):
    """图片处理错误"""
    pass

class PDFProcessor(Loader):
    """用于处理PDF文件的加载器，支持文本和图片提取
    
    特性：
    1. 提取PDF中的所有文本内容
    2. 提取PDF中的所有图片并保存
    3. 使用LLM分析图片内容
    4. 支持图片大小和格式限制
    5. 支持处理进度回调
    6. 支持并行处理多张图片
    7. 支持图片去重
    """
    
    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = {'jpeg', 'jpg', 'png', 'bmp', 'webp'}
    # 默认最大图片大小 (10MB)
    DEFAULT_MAX_IMAGE_SIZE = 10 * 1024 * 1024
    # 默认最大并行处理线程数
    DEFAULT_MAX_WORKERS = 4
    
    def __init__(self, **kwargs):
        super().__init__()
        self.max_image_size = kwargs.get('max_image_size', 10 * 1024 * 1024)  # 默认10MB
        self.progress_callback = kwargs.get('progress_callback', None)
        self.pdf_extract_images = kwargs.get('pdf_extract_images', True)
        self.skip_duplicate_images = kwargs.get('skip_duplicate_images', True)
        self._image_hashes = set()  # 用于图片去重
        
        # 设置日志级别为INFO
        log.setLevel(logging.INFO)
        
        # 确保static/images目录存在
        self.static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'static')
        self.images_dir = os.path.join(self.static_dir, 'images')
        os.makedirs(self.images_dir, exist_ok=True)
        
        log.info(f"Initialized PDFProcessor with static_dir: {self.static_dir}")
        log.info(f"Images will be saved to: {self.images_dir}")
        
    def _update_progress(self, stage: str, current: int, total: int):
        """更新处理进度
        
        Args:
            stage: 当前处理阶段
            current: 当前进度
            total: 总进度
        """
        if self.progress_callback:
            try:
                self.progress_callback(stage, current, total)
            except Exception as e:
                log.warning(f"Progress callback failed: {e}")
                
    def _get_image_hash(self, image_bytes: bytes) -> str:
        """计算图片哈希值
        
        Args:
            image_bytes: 图片数据
            
        Returns:
            str: 图片哈希值
        """
        return hashlib.md5(image_bytes).hexdigest()
                
    def _validate_image(self, image_bytes: bytes, format: str) -> bool:
        """验证图片是否符合要求
        
        Args:
            image_bytes: 图片数据
            format: 图片格式
            
        Returns:
            bool: 是否符合要求
        """
        # 检查大小
        if len(image_bytes) > self.max_image_size:
            log.warning(f"Image size ({len(image_bytes)} bytes) exceeds limit ({self.max_image_size} bytes)")
            return False
            
        # 检查格式
        if format.lower() not in self.SUPPORTED_IMAGE_FORMATS:
            log.warning(f"Unsupported image format: {format}")
            return False
            
        # 检查是否重复
        if self.skip_duplicate_images:
            image_hash = self._get_image_hash(image_bytes)
            if image_hash in self._image_hashes:
                log.info(f"Skipping duplicate image (hash: {image_hash})")
                return False
            self._image_hashes.add(image_hash)
            
        # 验证图片数据完整性
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            return True
        except Exception as e:
            log.warning(f"Image validation failed: {e}")
            return False
        
    def _save_image(self, image_bytes: bytes, file_info: dict, page_num: int, img_num: int) -> Tuple[str, str]:
        """保存图片并返回保存路径和hash值"""
        try:
            # 计算图片hash
            image_hash = hashlib.md5(image_bytes).hexdigest()[:8]
            
            # 创建以文件名为基础的子目录
            base_name = os.path.splitext(os.path.basename(file_info['filename']))[0]
            sub_dir = f"{base_name}_内容"
            image_dir = os.path.join(self.images_dir, sub_dir)
            os.makedirs(image_dir, exist_ok=True)
            
            # 构建图片文件名和保存路径
            image_filename = f"page_{page_num}_img_{img_num}_{image_hash}.jpeg"
            image_path = os.path.join(image_dir, image_filename)
            
            # 保存图片
            with open(image_path, 'wb') as f:
                f.write(image_bytes)
            
            log.info(f"Image saved successfully to: {image_path}")
            return image_path, image_hash
            
        except Exception as e:
            log.error(f"Error saving image: {str(e)}")
            raise
            
    def _get_image_url(self, image_path: str) -> str:
        """将图片路径转换为URL"""
        try:
            # 获取相对于static目录的路径
            rel_path = os.path.relpath(image_path, self.static_dir)
            # 转换为URL格式（使用正斜杠）
            url_path = rel_path.replace(os.sep, '/')
            # 构建完整URL（不使用相对路径）
            base_url = "http://chatgpt.nnit.cn:8696/static"
            final_url = f"{base_url}/{url_path}"
            
            log.info(f"Image URL conversion:")
            log.info(f"  Image path: {image_path}")
            log.info(f"  Static dir: {self.static_dir}")
            log.info(f"  Relative path: {rel_path}")
            log.info(f"  Final URL: {final_url}")
            
            return final_url
            
        except Exception as e:
            log.error(f"Error generating image URL: {str(e)}")
            raise

    def _generate_metadata(self, file_info: dict, image_info: Optional[dict] = None) -> Dict:
        """生成文档元数据
        
        Args:
            file_info: 文件信息，包含：
                - filename: 文件名
                - user_id: 用户ID
                - file_id: 文件ID
            image_info: 图片信息（可选），包含：
                - source: 图片路径
                - page_num: 页码
                - image_num: 图片序号
                - image_hash: 图片哈希值
                
        Returns:
            Dict: 元数据字典
        """
        metadata = {
            "name": file_info.get("filename", ""),
            "created_by": file_info.get("user_id", ""),
            "file_id": file_info.get("file_id", ""),
            "source": file_info.get("filename", ""),
        }
        
        if image_info:
            metadata.update({
                "type": "image_content",
                "image_source": self._get_image_url(image_info["source"]),
                "page_number": image_info.get("page_num", 0),
                "image_number": image_info.get("image_num", 0),
                "pdf_source": file_info.get("filename", ""),
                "image_hash": image_info.get("image_hash", "")
            })
        
        return metadata

    def _process_single_image(self, args: Tuple) -> Optional[Document]:
        """处理单张图片
        
        Args:
            args: (image_path, page_num, img_num, image_hash, file_info)
            
        Returns:
            Optional[Document]: 处理结果文档，如果处理失败则返回None
        """
        image_path, page_num, img_num, image_hash, file_info = args
        try:
            # 获取图片URL
            log.info("===============进入_process_single_image===============")
            image_url = self._get_image_url(image_path)
            log.info(f"=====pdf_processor/_process_single_image/image_url: =====\n {image_url}")
            
            # 构建LLM消息
            messages = [
                {"role": "system", "content": "extract information from image"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "extract information from image"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"{image_url}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            # 使用LLM分析图片
            result = (llm | StrOutputParser() ).invoke(messages)
            image_info = result.content if hasattr(result, 'content') else str(result)
            
            # 生成元数据
            metadata = self._generate_metadata(
                file_info,
                {
                    "source": image_path,
                    "page_num": page_num,
                    "image_num": img_num,
                    "image_hash": image_hash
                }
            )
            
            # 创建Document对象
            return Document(
                page_content=image_info,
                metadata=metadata
            )
            
        except Exception as e:
            log.error(f"处理图片失败: \nimage_path: {image_path}, \nimage_url: {image_url}, \n错误: {str(e)}")
            return None

    def extract_text(self, file_path: str) -> List[Document]:
        """提取PDF中的文本内容
        
        Args:
            file_path: PDF文件路径
        
        Returns:
            List[Document]: 包含文本内容的Document列表
            
        Raises:
            PDFProcessError: PDF处理失败
        """
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            self._update_progress("text_extraction", 1, 1)
            return documents
        except Exception as e:
            raise PDFProcessError(f"Failed to extract text: {e}")

    def extract_images(self, file_path: str) -> List[Tuple[str, int, int, str]]:
        """提取PDF中的图片并保存
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            List[Tuple[str, int, int, str]]: 保存的图片路径、页码、图片序号和哈希值的列表
            
        Raises:
            PDFProcessError: 图片提取失败
        """
        if not self.pdf_extract_images:
            return []
            
        try:
            pdf_document = fitz.open(file_path)
            image_info_list = []
            # 获取所有图片数量
            total_images = sum(len(page.get_images()) for page in pdf_document)
            processed_images = 0

            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = pdf_document.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # 计算图片哈希值
                        image_hash = self._get_image_hash(image_bytes)
                        
                        # 验证图片
                        if not self._validate_image(image_bytes, base_image['ext']):
                            processed_images += 1
                            self._update_progress("image_extraction", processed_images, total_images)
                            continue
                        
                        # 保存图片
                        image_path, image_hash = self._save_image(image_bytes, {"filename": file_path}, page_num + 1, img_index + 1)
                        
                        image_info_list.append((image_path, page_num + 1, img_index + 1, image_hash))
                        
                    except Exception as e:
                        log.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
                    finally:
                        processed_images += 1
                        self._update_progress("image_extraction", processed_images, total_images)
                    
            pdf_document.close()
            return image_info_list
            
        except Exception as e:
            raise PDFProcessError(f"Failed to extract images: {e}")

    def process_images_with_llm(self, image_info_list: List[Tuple[str, int, int, str]], file_info: dict) -> List[Document]:
        """使用LLM处理图片内容
        
        Args:
            image_info_list: 图片信息列表，每项包含(路径, 页码, 图片序号, 哈希值)
            file_info: 文件信息
            
        Returns:
            List[Document]: 包含图片内容描述的Document列表
            
        Raises:
            PDFProcessError: LLM处理失败
        """
        documents = []
        total_images = len(image_info_list)
        processed_images = 0
        
        # 准备处理参数
        process_args = [(path, page_num, img_num, img_hash, file_info) 
                       for path, page_num, img_num, img_hash in image_info_list]
        
        # 使用线程池并行处理图片
        with ThreadPoolExecutor(max_workers=self.DEFAULT_MAX_WORKERS) as executor:
            future_to_image = {executor.submit(self._process_single_image, args): args 
                             for args in process_args}
            
            for future in concurrent.futures.as_completed(future_to_image):
                processed_images += 1
                self._update_progress("llm_processing", processed_images, total_images)
                
                try:
                    doc = future.result()
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    image_path = future_to_image[future][0]
                    log.error(f"Failed to process image {image_path}: {e}")
        
        return documents

    def load(self, filename: str, file_content_type: str, file_path: str) -> List[Document]:
        """加载PDF文件，提取文本和图片内容
        
        Args:
            filename: 文件名
            file_content_type: 文件类型
            file_path: 文件路径
            
        Returns:
            List[Document]: 包含所有内容的Document列表
            
        Raises:
            PDFProcessError: 处理失败
        """
        try:
            # 清理图片哈希集合
            self._image_hashes.clear()
            
            # 提取文本
            text_documents = self.extract_text(file_path)
            
            # 提取并处理图片
            image_info_list = self.extract_images(file_path)
            
            # 准备文件信息
            file_info = {
                "filename": filename,
                "file_id": os.path.splitext(filename)[0],  # 临时使用文件名作为ID
                "user_id": "system"  # 需要从上下文获取
            }
            
            # 处理图片
            image_documents = self.process_images_with_llm(image_info_list, file_info)
            
            # 合并所有文档
            return text_documents + image_documents
            
        except Exception as e:
            raise PDFProcessError(f"Failed to process PDF {filename}: {e}")
