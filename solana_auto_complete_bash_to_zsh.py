import re
import sys

def extract_commands_and_opts(bash_script):
    """提取命令和它们的选项以及子命令"""
    commands = {}
    current_cmd = None
    subcmd_pattern = re.compile(r'solana__([a-zA-Z_]+)')
    
    # 查找形如 "solana)" 或 "solana__command)" 的命令定义
    cmd_pattern = re.compile(r'\s+(solana(?:__[a-zA-Z_]+)?)\)')
    # 查找选项定义
    opts_pattern = re.compile(r'\s+opts="([^"]+)"')
    
    def normalize_subcmd(cmd):
        """将bash补全中的命令名转换为实际命令名"""
        return cmd.replace('__', '-')
    
    for line in bash_script.split('\n'):
        # 尝试匹配命令
        cmd_match = cmd_pattern.match(line)
        if cmd_match:
            current_cmd = cmd_match.group(1)
            if current_cmd == 'solana':
                # 处理主命令
                if current_cmd not in commands:
                    commands[current_cmd] = {
                        'opts': set(),
                        'subcommands': set()
                    }
            else:
                # 处理子命令
                subcmd_match = subcmd_pattern.match(current_cmd)
                if subcmd_match:
                    subcmd = normalize_subcmd(subcmd_match.group(1))
                    if 'solana' not in commands:
                        commands['solana'] = {'opts': set(), 'subcommands': set()}
                    commands['solana']['subcommands'].add(subcmd)
                    if subcmd not in commands:
                        commands[subcmd] = {'opts': set()}
            continue
            
        # 尝试匹配选项
        if current_cmd:
            opts_match = opts_pattern.match(line)
            if opts_match:
                opts_str = opts_match.group(1)
                # 处理引号内的选项
                opts = re.findall(r'(?:--?[a-zA-Z-]+=?|\[[^\]]+\]|\S+)', opts_str)
                # 只保留以 - 开头的选项
                valid_opts = set()
                for opt in opts:
                    if opt.startswith('-'):
                        # 处理带参数的选项
                        if '=' in opt:
                            opt = opt[:-1]  # 移除 =
                        valid_opts.add(opt)
                
                if current_cmd == 'solana':
                    commands['solana']['opts'].update(valid_opts)
                else:
                    subcmd = normalize_subcmd(subcmd_pattern.match(current_cmd).group(1))
                    commands[subcmd]['opts'].update(valid_opts)
    
    return commands

def generate_zsh_completion(commands):
    """生成 zsh completion 脚本"""
    zsh_script = [
        '#compdef solana',
        '',
        '_solana() {',
        '    local context state state_descr line ret=1',
        '    local curcontext="$curcontext"',
        '',
        '    typeset -A opt_args',
        '    local -a main_commands',
        '',
        '    # Define subcommands',
        '    main_commands=('
    ]
    
    # 添加主命令的子命令
    if 'solana' in commands:
        subcommands = commands['solana']['subcommands']
        for subcmd in sorted(subcommands):
            clean_subcmd = subcmd.replace("'", "''")  # Escape single quotes
            zsh_script.append(f"        '{clean_subcmd}:Solana {clean_subcmd} command'")
    
    zsh_script.extend([
        '    )',
        '',
        '    # Main argument handling',
        '    _arguments -C \\',
    ])
    
    # 添加主命令的选项
    if 'solana' in commands:
        main_opts = commands['solana']['opts']
        for opt in sorted(main_opts):
            if opt.startswith('--'):
                desc = opt[2:].replace('-', ' ')
                zsh_script.append(f"        '{opt}[{desc}]' \\")
            else:
                zsh_script.append(f"        '{opt}' \\")
    
    zsh_script.extend([
        "        '(-h --help)'{-h,--help}'[Show help information]' \\",
        "        '1: :->cmds' \\",
        "        '*:: :->args' && ret=0",
        '',
        '    case $state in',
        '        cmds)',
        '            _describe -t commands "solana command" main_commands && ret=0',
        '            ;;',
        '        args)',
        '            curcontext="${curcontext%:*:*}:solana-$words[1]:"',
        '            case $words[1] in'
    ])
    
    # 为每个子命令生成选项
    if 'solana' in commands:
        for subcmd in sorted(commands['solana']['subcommands']):
            if subcmd in commands:
                opts = commands[subcmd]['opts']
                if opts:
                    clean_subcmd = subcmd.replace('-', '_')  # 替换连字符为下划线
                    zsh_script.append(f'                {clean_subcmd})')
                    zsh_script.append('                    _arguments \\')
                    for opt in sorted(opts):
                        if opt.startswith('--'):
                            desc = opt[2:].replace('-', ' ')
                            zsh_script.append(f"                        '{opt}[{desc}]' \\")
                        else:
                            zsh_script.append(f"                        '{opt}' \\")
                    # 添加通用帮助选项
                    zsh_script.append("                        '(-h --help)'{-h,--help}'[Show help information]' \\")
                    zsh_script.append("                        '*::arg:->args'")
                    zsh_script.append('                    ;;')
    
    # 添加结尾
    zsh_script.extend([
        '            esac',
        '            ;;',
        '    esac',
        '',
        '    return ret',
        '}',
        '',
        '_solana "$@"'
    ])
    
    return '\n'.join(zsh_script)

def main():
    # 从标准输入读取bash completion脚本
    bash_script = sys.stdin.read()
    
    # 提取命令和选项
    commands = extract_commands_and_opts(bash_script)
    
    # 生成并输出zsh completion脚本
    zsh_script = generate_zsh_completion(commands)
    print(zsh_script)

if __name__ == '__main__':
    main()