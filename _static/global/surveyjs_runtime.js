(function() {
    function defaultErrorHtml() {
        return '<div class="alert alert-danger mb-0">Could not load the survey. Please reload the page.</div>';
    }

    function renderSurvey(options) {
        var config = options || {};
        var containerId = config.containerId || 'surveyContainer';
        var hiddenFieldId = config.hiddenFieldId || 'surveyResults';
        var formId = config.formId || 'form';
        var hooks = config.hooks || {};

        var container = document.getElementById(containerId);
        if (!container) {
            throw new Error('Survey container not found: ' + containerId);
        }

        if (typeof Survey === 'undefined' || !Survey.Model) {
            throw new Error('SurveyJS library is not loaded.');
        }

        var survey = new Survey.Model(config.surveyJson || {});
        survey.showPrevButton = false;
        survey.showCompletedPage = false;

        if (typeof hooks.onTextMarkdown === 'function') {
            survey.onTextMarkdown.add(hooks.onTextMarkdown);
        }
        if (typeof hooks.onCurrentPageChanged === 'function') {
            survey.onCurrentPageChanged.add(hooks.onCurrentPageChanged);
        }
        if (typeof hooks.beforeRender === 'function') {
            hooks.beforeRender(survey);
        }

        survey.onComplete.add(function(sender) {
            if (typeof hooks.onComplete === 'function') {
                hooks.onComplete(sender);
                return;
            }

            var hiddenField = document.getElementById(hiddenFieldId);
            if (!hiddenField) {
                throw new Error('Hidden survey field not found: ' + hiddenFieldId);
            }

            hiddenField.value = JSON.stringify(sender.data || {});
            var form = document.getElementById(formId);
            if (!form) {
                throw new Error('Form not found: ' + formId);
            }
            form.submit();
        });

        survey.render(container);
        return survey;
    }

    function renderSurveySafely(options) {
        try {
            return renderSurvey(options);
        } catch (error) {
            console.error('Failed to initialize SurveyJS:', error);
            var containerId = (options && options.containerId) || 'surveyContainer';
            var container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = (options && options.errorHtml) || defaultErrorHtml();
            }
            return null;
        }
    }

    window.SurveyJSRuntime = {
        renderSurvey: renderSurvey,
        renderSurveySafely: renderSurveySafely,
    };
})();
