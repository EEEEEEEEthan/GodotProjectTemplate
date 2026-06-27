"""测试jack agent配置是否正确"""

import sys
import os

# 添加.egent到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from workflow.agent_definition import get_definition, AGENTS


def test_jack_exists():
    """测试jack配置是否存在"""
    assert "jack" in AGENTS, "jack配置不存在"
    print("✓ jack配置存在")


def test_jack_basic_info():
    """测试jack基本信息"""
    jack = get_definition("jack")
    assert jack.name == "jack", f"名称错误: {jack.name}"
    assert jack.key == "volc", f"key错误: {jack.key}"
    assert jack.model == "deepseek-v4-pro-260425", f"model错误: {jack.model}"
    print("✓ jack基本信息正确")


def test_jack_system_prompt():
    """测试jack系统提示词"""
    jack = get_definition("jack")
    assert ".egent" in jack.system_prompt, "系统提示词未提及.egent"
    assert "nahte的手下" in jack.system_prompt, "系统提示词未提及nahte的手下"
    print("✓ jack系统提示词正确")


def test_jack_ignore_files_same_as_nahte():
    """测试jack的ignore_files与nahte完全一致"""
    jack = get_definition("jack")
    nahte = get_definition("nahte")
    assert jack.ignore_files == nahte.ignore_files, (
        f"jack的ignore_files与nahte不一致:\n"
        f"  jack:  {jack.ignore_files}\n"
        f"  nahte: {nahte.ignore_files}"
    )
    print("✓ jack ignore_files与nahte完全一致")


def test_jack_no_skills():
    """测试jack没有配置skills"""
    jack = get_definition("jack")
    assert len(jack.skills) == 0, f"jack不应该有skills: {jack.skills}"
    print("✓ jack没有配置外部skills")


def test_other_agents_unaffected():
    """测试其他agent配置未被影响"""
    nahte = get_definition("nahte")
    egent = get_definition("egent")
    jason = get_definition("jason")

    assert nahte.name == "nahte"
    assert egent.name == "egent"
    assert jason.name == "jason"

    # nahte不应该忽略.egent
    assert ".egent" not in nahte.ignore_files

    # jason应该忽略.egent
    assert ".egent" in jason.ignore_files

    # egent不应该忽略.egent
    assert ".egent" not in egent.ignore_files

    print("✓ 其他agent配置未被影响")


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("测试jack配置")
    print("=" * 50)

    tests = [
        test_jack_exists,
        test_jack_basic_info,
        test_jack_system_prompt,
        test_jack_ignore_files_same_as_nahte,
        test_jack_no_skills,
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
