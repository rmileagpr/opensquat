#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Module: cli.py
"""
openSquat CLI entry point.

* https://github.com/atenreiro/opensquat

software licensed under GNU version 3
"""
import time
import signal
import functools
import concurrent.futures

from colorama import init, Fore, Style
from opensquat import __VERSION__, vt
from opensquat import arg_parser, output, app, phishing, check_update
from opensquat import port_check
from opensquat.app import ApiOptions


def signal_handler(sig, frame):
    """Function to catch CTR+C and terminate."""
    print("\n[*] openSquat is terminating...\n")
    exit(0)


def _print_mode_summary(mode, scanner):
    """Print the mode-specific lines of the run summary."""
    if mode == "premium_feed":
        print("[*] Mode: Premium Feed")
        return
    if mode != "premium_api":
        return
    print("[*] Mode: Premium API")

    # If the run was cut short (rate limit or quota exhaustion), show the
    # shortfall ratio so the user can tell at a glance that not every
    # requested keyword was processed.
    total = scanner.keywords_total
    made = scanner.api_calls_made
    if total and made < total:
        print(f"[*] API calls made: {made} (of {total})")
    else:
        print("[*] API calls made:", made)

    if scanner.api_balance is not None:
        initial = scanner.api_balance_initial
        if initial is not None and initial > scanner.api_balance:
            used = initial - scanner.api_balance
            print(
                "[*] API balance remaining:",
                f"{scanner.api_balance} (used {used} of {initial} this run)"
            )
        else:
            print("[*] API balance remaining:", scanner.api_balance)

    # Reason line when the run ended early. rate_limited is transient and
    # shown in yellow; quota exhaustion is shown in red and implied by the
    # forced-zero balance above.
    if scanner.rate_limited:
        print(
            Style.BRIGHT + Fore.YELLOW +
            "[*] Rate limit hit - wait a few seconds before retrying "
            "the remaining keywords" +
            Style.RESET_ALL
        )
    elif total and made < total and scanner.api_balance == 0:
        print(
            Style.BRIGHT + Fore.RED +
            "[*] Quota exhausted - upgrade your plan or wait for the "
            "monthly reset" +
            Style.RESET_ALL
        )


def main():
    signal.signal(signal.SIGINT, signal_handler)

    init()

    logo = (
        Style.BRIGHT + Fore.GREEN +
        """
                                             █████████                                  █████
                                            ███░░░░░███                                ░░███
      ██████  ████████   ██████  ████████  ░███    ░░░   ████████ █████ ████  ██████   ███████
     ███░░███░░███░░███ ███░░███░░███░░███ ░░█████████  ███░░███ ░░███ ░███  ░░░░░███ ░░░███░
    ░███ ░███ ░███ ░███░███████  ░███ ░███  ░░░░░░░░███░███ ░███  ░███ ░███   ███████   ░███
    ░███ ░███ ░███ ░███░███░░░   ░███ ░███  ███    ░███░███ ░███  ░███ ░███  ███░░███   ░███ ███
    ░░██████  ░███████ ░░██████  ████ █████░░█████████ ░░███████  ░░████████░░████████  ░░█████
     ░░░░░░   ░███░░░   ░░░░░░  ░░░░ ░░░░░  ░░░░░░░░░   ░░░░░███   ░░░░░░░░  ░░░░░░░░    ░░░░░
              ░███                                          ░███
              █████                                         █████
             ░░░░░                                         ░░░░░
                    (c) openSquat - https://opensquat.com
    """ + Style.RESET_ALL
    )

    print(logo)
    print("\t\t\tversion " + __VERSION__ + "\n")

    args = arg_parser.get_args()

    # Usability hint: if the user provided --api-key but didn't pick a mode
    # that uses it, tell them it's being ignored. Don't auto-switch modes.
    if args.mode == "community" and args.api_key:
        print(
            Style.BRIGHT + Fore.YELLOW +
            "[!] --api-key was provided but no mode that uses it was selected.\n"
            "    Running in community mode; the key will be ignored.\n"
            "    Add --premium (to download the paid feed) or --api (to query\n"
            "    the lookalike REST API) to use it." +
            Style.RESET_ALL
        )

    # Mode-specific incompatibilities (early-fail before any work)
    if args.mode == "premium_api" and args.doppelganger:
        print(
            Style.BRIGHT + Fore.RED +
            "[ERROR] --doppelganger is incompatible with --api.\n"
            "        --doppelganger runs local substring matching plus per-domain "
            "HTTP and CT\n"
            "        checks on a candidate set produced from a downloaded feed. "
            "The API\n"
            "        replaces candidate-set generation and does not return "
            "doppelganger\n"
            "        candidates. Workaround: omit --api to run doppelganger "
            "against the\n"
            "        local feed." +
            Style.RESET_ALL
        )
        exit(-1)

    if args.mode == "premium_api" and args.domains:
        print(
            Style.BRIGHT + Fore.RED +
            "[ERROR] -d/--domains is incompatible with --api. "
            "API mode does not read a local feed." +
            Style.RESET_ALL
        )
        exit(-1)

    start_time_squatting = time.time()

    api_options = None
    if args.mode == "premium_api":
        api_options = ApiOptions(
            api_key=args.resolved_api_key,
            fuzziness=args.api_fuzziness,
            history_days=args.api_history_days,
            max_results=args.api_max_results,
            rate_limit=args.api_rate_limit,
        )

    domain_scanner = app.Domain()
    file_content = domain_scanner.main(
        args.keywords,
        args.confidence,
        args.domains,
        args.dns,
        doppelganger_only=args.doppelganger,
        feed_url=args.url,
        mode=args.mode,
        api_options=api_options,
        premium_api_key=args.resolved_api_key if args.mode == "premium_feed" else None,
    )

    if args.subdomains or args.vt or args.phishing or args.portcheck:
        print("\n[*] Total found:", len(file_content))

    # Check for subdomains
    if (args.subdomains):
        list_aux = []
        print("\n+---------- Checking for Subdomains ----------+")
        time.sleep(1)
        for domain in file_content:
            print("[*]", domain)
            subdomains = vt.VirusTotal().main(domain, "subdomains")

            if subdomains:
                for subdomain in subdomains:
                    print(
                        Style.BRIGHT + Fore.YELLOW +
                        " \\_", subdomain +
                        Style.RESET_ALL,
                        )
                    list_aux.append(subdomain)
        file_content = list_aux
        print("[*] Total found:", len(file_content))

    # Check for VirusTotal (if domain is flagged as malicious)
    if (args.vt):
        list_aux = []
        print("\n+---------- VirusTotal ----------+")
        time.sleep(1)
        for domain in file_content:
            total_votes = vt.VirusTotal().main(domain)

            # total_votes layout: (harmless, malicious). We only act on the
            # malicious count; the harmless count is unused but kept in the
            # tuple to preserve the vt.VirusTotal.main() return contract.
            malicious = total_votes[1]

            if malicious > 0:
                print(
                    Style.BRIGHT + Fore.RED +
                    "[*] found:", domain, "({})".format(str(malicious)) +
                    Style.RESET_ALL,
                    )
                list_aux.append(domain)
            elif malicious < 0:
                print(
                    Style.BRIGHT + Fore.YELLOW +
                    "[*] VT is throttling the response:", domain +
                    Style.RESET_ALL,
                    )
                list_aux.append(domain)
        file_content = list_aux
        print("[*] Total found:", len(file_content))

    # Check for phishing
    if (args.phishing != ""):
        file_phishing = phishing.Phishing().main(args.keywords)
        output.SaveFile().main(args.phishing, "txt", file_phishing)

    # Check if domain has webserver port opened
    if (args.portcheck):
        list_aux = []
        print("\n+---------- Domains with open webserver ports ----------+")
        time.sleep(1)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futs = [(domain, executor.submit(functools.partial(port_check.PortCheck().main, domain)))
                    for domain in file_content]

        for tested_domain, result_domain_port_check in futs:
            ports = result_domain_port_check.result()
            if ports:
                list_aux.append(tested_domain)
                print(
                    Fore.YELLOW +
                    "[*]", tested_domain, ports, "" +
                    Style.RESET_ALL
                    )

        file_content = list_aux
        print("[*] Total found:", len(file_content))

    if args.type == "json":
        filtered_set = set(file_content)
        json_content = []
        for kw, doms in domain_scanner.keyword_domains.items():
            filtered_doms = [d for d in doms if d in filtered_set]
            if filtered_doms:
                json_content.append({"keyword": kw, "domains": filtered_doms})
        output.SaveFile().main(args.output, args.type, json_content)
    else:
        output.SaveFile().main(args.output, args.type, file_content)
    end_time_squatting = round(time.time() - start_time_squatting, 2)

    # Print summary
    print("\n")
    print(
        Style.BRIGHT+Fore.GREEN +
        "+---------- Summary Squatting ----------+" +
        Style.RESET_ALL)

    print("[*] Domains flagged:", len(file_content))
    print("[*] Domains result:", args.output)

    _print_mode_summary(args.mode, domain_scanner)

    if (args.phishing != ""):
        print("[*] Phishing results:", args.phishing)
        print("[*] Active Phishing sites:", len(file_phishing))

    print("[*] Running time: %s seconds" % end_time_squatting)
    print("")

    check_update.CheckUpdate().main()


if __name__ == "__main__":
    main()
