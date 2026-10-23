(function () {
"use strict";



function add_language_switcher() {

    if (document.querySelector(".kenz-language-switcher")) {
        return;
    }


    const navbarNav = document.querySelector(
        ".navbar .collapse.navbar-collapse > ul.navbar-nav"
    );

    if (!navbarNav) {
        setTimeout(add_language_switcher, 500);
        return;
    }

    const currentLanguage =
        frappe.boot &&
        frappe.boot.lang
            ? frappe.boot.lang
            : "en";

    const currentLabel =
        currentLanguage === "ar"
            ? "🇸🇦 AR"
            : "🇺🇸 EN";

    const wrapper = document.createElement("li");

    wrapper.className =
        "nav-item dropdown dropdown-mobile kenz-language-switcher";

    wrapper.innerHTML = `
        <a
            href="#"
            class="nav-link kenz-language-button"
            aria-label="Language"
            title="Language"
        >
            <span class="kenz-current-language">
                ${currentLabel}
            </span>
        </a>

        <div
            class="dropdown-menu dropdown-menu-right kenz-language-menu"
            role="menu"
        >

            <a
                href="#"
                class="dropdown-item kenz-language-option"
                data-language="en"
            >
                🇺🇸 English
            </a>

            <a
                href="#"
                class="dropdown-item kenz-language-option"
                data-language="ar"
            >
                🇸🇦 العربية
            </a>

        </div>
    `;

    const notifications =
        navbarNav.querySelector(".dropdown-notifications");

    if (notifications) {
        notifications.after(wrapper);
    } else {
        navbarNav.appendChild(wrapper);
    }

    const button =
        wrapper.querySelector(".kenz-language-button");

    const menu =
        wrapper.querySelector(".kenz-language-menu");

    button.addEventListener("click", function (e) {

        e.preventDefault();
        e.stopPropagation();

        document
            .querySelectorAll(
                ".navbar .dropdown-menu.show"
            )
            .forEach(function (dropdown) {

                if (dropdown !== menu) {
                    dropdown.classList.remove("show");
                }

            });

        menu.classList.toggle("show");

    });


    document.addEventListener("click", function (e) {

        if (!wrapper.contains(e.target)) {
            menu.classList.remove("show");
        }

    });

    wrapper
        .querySelectorAll(".kenz-language-option")
        .forEach(function (item) {

            item.addEventListener(
                "click",
                function (e) {

                    e.preventDefault();
                    e.stopPropagation();

                    const language =
                        this.getAttribute("data-language");


                    wrapper
                        .querySelectorAll(
                            ".kenz-language-option"
                        )
                        .forEach(function (option) {

                            option.style.pointerEvents =
                                "none";

                            option.style.opacity =
                                "0.5";

                        });

                    frappe.call({

                        method:
                            "kenz_trading.events.language.change_language",

                        args: {
                            language: language
                        },

                        freeze: true,

                        freeze_message:
                            language === "ar"
                                ? "جاري تغيير اللغة..."
                                : "Changing language...",

                        callback: function (r) {

                            if (r.exc) {

                                frappe.msgprint(
                                    __("Unable to change language")
                                );

                                wrapper
                                    .querySelectorAll(
                                        ".kenz-language-option"
                                    )
                                    .forEach(
                                        function (option) {

                                            option.style.pointerEvents =
                                                "";

                                            option.style.opacity =
                                                "";

                                        }
                                    );

                                return;
                            }


                            localStorage.setItem(
                                "active_lang",
                                language.toUpperCase()
                            );

                            setTimeout(
                                function () {

                                    window.location.reload();

                                },
                                300
                            );

                        }

                    });

                }
            );

        });
}


setTimeout(
    add_language_switcher,
    1000
);


})();
