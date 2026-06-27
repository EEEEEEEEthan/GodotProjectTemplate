"""测试nahte agent配置是否正确"""

import sys
import os

# 添加.egent到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow.agent_definition import get_definition, AGENTS


def test_nahte_exists():
    """测试nahte配置是否存在"""
    assert "nahte" in AGENTS, "nahte配置不存在"
    print("✓ nahte配置存在")


def test_nahte_basic_info():
    """测试nahte基本信息"""
    nahte = get_definition("nahte")
    assert nahte.name == "nahte", f"名称错误: {nahte.name}"
    assert nahte.key == "volc", f"key错误: {nahte.key}"
    assert nahte.model == "deepseek-v4-pro-260425", f"model错误: {nahte.model}"
    print("✓ nahte基本信息正确")


def test_nahte_system_prompt():
    """测试nahte系统提示词"""
    nahte = get_definition("nahte")
    assert ".egent" in nahte.system_prompt, "系统提示词未提及.egent"
    assert "绝不触碰.egent/以外的任何文件" in nahte.system_prompt, "系统提示词未强调边界"
    print("✓ nahte系统提示词正确")


def test_nahte_ignore_files():
    """测试nahte的ignore_files配置"""
    nahte = get_definition("nahte")
    
    # 应该忽略的目录和文件
    should_ignore = [
        "addons",
        ".engine",
        "test",
        "tests",
        "*.tscn",
        "*.gd",
        "*.cs",
    ]
    
    for pattern in should_ignore:
        assert pattern in nahte.ignore_files, f"应该忽略: {pattern}"
    
    # 不应该忽略.egent
    assert ".egent" not in nahte.ignore_files, "不应该忽略.egent"
    
    print("✓ nahte ignore_files配置正确")


def test_nahte_no_skills():
    """测试nahte没有配置skills（因为只负责.egent开发内）"""
    nahte = get_definition("nahte")
    assert len(nahte.skills) == 0, f"nahte不应该有skills: {nahte.skills}"
    print("✓ nahte没有配置外部skills")


def test_other_agents_unaffected():
    """测试其他agent配置未被影响"""
    jason = get_definition("jason")
    egent = get_definition("egent")
    
    assert jason.name == "jason"
    assert egent.name == "egent"
    
    # jason应该忽略.egent
    assert ".egent" in jason.ignore_files
    
    # egent不应该忽略.egent
    assert ".egent" not in egent.ignore_files
    
    print("✓ 其他agent配置未被影响")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("测试nahte配置")
    print("=" * 50)
    
    tests = [
        test_nahte_exists,
        test_nahte_basic_info,
        test_nahte_system_prompt,
        test_nahte_ignore_files,
        test_nahte_no_skills,
        test_other_agents_unaffected,
    ]
    
    failed = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} 失败: {e}")
            failed.append(test.__name__)
        except Exception as e:
            print(f"✗ {test.__name__} 异常: {e}")
            failed.append(test.__name__)
    
    print("=" * 50)
    if failed:
        print(f"失败: {len(failed)}/{len(tests)}")
        for name in failed:
            print(f"  - {name}")
        return False
    else:
        print(f"成功: {len(tests)}/{len(tests)}")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
