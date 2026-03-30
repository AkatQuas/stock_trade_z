import importlib
import json
import sys
from typing import Any, Dict, List

from .logger import get_logger
from .paths import get_file_in_pack

logger = get_logger("noop")


def load_config() -> List[Dict[str, Any]]:
    cfg_path = get_file_in_pack("./selector.config.json")
    with cfg_path.open(encoding="utf-8") as f:
        cfg_raw = json.load(f)

    # 兼容三种结构：单对象、对象数组、或带 selectors 键
    if isinstance(cfg_raw, list):
        cfg = cfg_raw
    elif isinstance(cfg_raw, dict) and "selectors" in cfg_raw:
        cfg = cfg_raw["selectors"]
    else:
        cfg = [cfg_raw]

    if not cfg:
        logger.error("configs.json 未定义任何 Selector")
        sys.exit(1)

    return cfg


def instantiate_selector(cfg: Dict[str, Any]):
    """动态加载 Selector 类并实例化"""
    cls_name: str | None = cfg.get("class")
    if not cls_name:
        raise ValueError("缺少 class 字段")

    try:
        module = importlib.import_module("lib.selector")
        cls = getattr(module, cls_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(f"无法加载 selector.{cls_name}: {e}") from e

    params = cfg.get("params", {})
    return cfg.get("alias", cls_name), cls(**params)


def load_selector():
    selector_cfg = load_config()
    result = {}
    for cfg in selector_cfg:
        try:
            alias, selector = instantiate_selector(cfg)
            result[alias] = selector
        except Exception as e:
            logger.error("跳过配置 %s : %s", cfg, e)
            continue
    return result


if __name__ == "__main__":
    r = load_selector()

    for key, value in r.items():
        print(key)
        print(value)
