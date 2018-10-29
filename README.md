# Android编译依赖冲突检查工具

检查在dexMerger阶段不同库存在相同包名导致的合并冲突。

运行环境 python3.7+

用法:python main.py --verbose project/appmodule

将输出所有有冲突的依赖及类信息（仅当打开--verbose开关)